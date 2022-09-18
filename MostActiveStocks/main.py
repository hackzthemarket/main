from AlgorithmImports import *
class VerticalTachyonRegulators(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2021, 1, 7)
        self.SetEndDate(2022, 9, 27)
        self.SetCash(10000)

        # Universe selection
        self.num_coarse = 500
        self.rebalanceTime = datetime.min

        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddUniverse(self.CoarseSelectionFunction)
        
        # Alpha Model
        self.AddAlpha(ConstantAlphaModel())
        # Portfolio construction model
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        self.SetRiskManagement(NullRiskManagementModel())
        # Execution model
        self.SetExecution(ImmediateExecutionModel())

    # Share the same rebalance function for Universe and PCM for clarity
    def IsRebalanceDue(self, time):
        # Rebalance on the first day of the Quarter
        if self.Time <= self.rebalanceTime:
            return False
        
        self.Liquidate()
        self.rebalanceTime = self.Time + timedelta(1)
        return True

    def CoarseSelectionFunction(self, coarse):
        # If not time to rebalance, keep the same universe
        if self.IsRebalanceDue(self.Time) == False: 
            return Universe.Unchanged

        # Select only those with fundamental data and a sufficiently large price
        # Sort by top dollar volume: most liquid to least liquid
        selected = sorted([x for x in coarse if x.Price > 0],
                            key = lambda x: x.Volume, reverse=True)

        return [x.Symbol for x in selected[:self.num_coarse]]
        
    def FineFilter(self, fine):
        return [x.Symbol for x in fine if x.CompanyReference.CountryId == "USA"
                                                and x.CompanyReference.PrimaryExchangeID in ["NYS","NAS"]][:500]        
        return filtered_fine



class ConstantAlphaModel(AlphaModel):
    ''' Provides an implementation of IAlphaModel that always returns the same insight for each security'''

    def __init__(self):
        '''Initializes a new instance of the ConstantAlphaModel class
        Args:
            type: The type of insight
            direction: The direction of the insight
            period: The period over which the insight with come to fruition
            magnitude: The predicted change in magnitude as a +- percentage
            confidence: The confidence in the insight'''
        self.rebalanceTime = datetime.min
        self.securities = []
        self.insightsTimeBySymbol = {}
        self.historyArray = {}

    def Update(self, algorithm, data):
        ''' Creates a constant insight for each security as specified via the constructor
        Args:
            algorithm: The algorithm instance
            data: The new data available
        Returns:
            The new insights generated'''
        if algorithm.Time <= self.rebalanceTime:
            return []

        self.rebalanceTime = algorithm.Time + timedelta(1)

        insights = []
        
        sortedList = sorted(self.securities, key=lambda x: x.Volume, reverse=True)[:10]

        for x in sortedList:
            insights.append(Insight.Price(x.Symbol, timedelta(1), InsightDirection.Up))
                
        return insights

    def OnSecuritiesChanged(self, algorithm, changes):
        ''' Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm'''
                # this will allow the insight to be re-sent when the security re-joins the universe
        for removed in changes.RemovedSecurities:
            if removed in self.securities:
                self.securities.remove(removed)
            if removed.Symbol in self.insightsTimeBySymbol:
                self.insightsTimeBySymbol.pop(removed.Symbol)
        
        for added in changes.AddedSecurities:
            self.securities.append(added)


    def ShouldEmitInsight(self, utcTime, symbol):

        generatedTimeUtc = self.insightsTimeBySymbol.get(symbol)

        if generatedTimeUtc is not None:
            # we previously emitted a insight for this symbol, check it's period to see
            # if we should emit another insight
            if utcTime - generatedTimeUtc < self.period:
                return False

        # we either haven't emitted a insight for this symbol or the previous
        # insight's period has expired, so emit a new insight now for this symbol
        self.insightsTimeBySymbol[symbol] = utcTime
        return True
