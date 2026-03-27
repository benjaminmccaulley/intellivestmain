const yahooFinance = require('yahoo-finance2').default;

/**
 * Fetch real-time stock information using yahoo-finance2
 */

async function getRealTimeStockInfo(symbol) {
    try {
        const quote = await yahooFinance.quote(symbol);
        
        return {
            symbol: quote.symbol,
            price: quote.regularMarketPrice,
            currency: quote.currency,
            marketState: quote.marketState,
            regularMarketTime: quote.regularMarketTime,
            regularMarketChange: quote.regularMarketChange,
            regularMarketChangePercent: quote.regularMarketChangePercent,
            regularMarketVolume: quote.regularMarketVolume,
            marketCap: quote.marketCap,
            dayHigh: quote.regularMarketDayHigh,
            dayLow: quote.regularMarketDayLow,
            previousClose: quote.regularMarketPreviousClose,
            bid: quote.bid,
            ask: quote.ask,
            bidSize: quote.bidSize,
            askSize: quote.askSize,
            timestamp: new Date().toISOString()
        };
    } catch (error) {
        throw new Error(`Error fetching stock info for ${symbol}: ${error.message}`);
    }
}

async function getStockHistory(symbol, period = '1mo', interval = '1d') {
    try {
        const queryOptions = {
            period1: getPeriodStartDate(period),
            interval: interval,
            includeAdjustedClose: true
        };
        
        const historicalData = await yahooFinance.historical(symbol, queryOptions);
        
        return historicalData.map(item => ({
            date: item.date,
            open: item.open,
            high: item.high,
            low: item.low,
            close: item.close,
            volume: item.volume,
            adjustedClose: item.adjClose
        }));
    } catch (error) {
        throw new Error(`Error fetching stock history for ${symbol}: ${error.message}`);
    }
}

function getPeriodStartDate(period) {
    const now = new Date();
    const periods = {
        '1d': 1,
        '5d': 5,
        '1mo': 30,
        '3mo': 90,
        '6mo': 180,
        '1y': 365,
        '2y': 730,
        '5y': 1825
    };
    
    const days = periods[period] || 30;
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - days);
    
    return Math.floor(startDate.getTime() / 1000);
}

async function getMultipleStocks(symbols) {
    try {
        const quotes = await yahooFinance.quote(symbols);
        
        if (Array.isArray(quotes)) {
            return quotes.map(quote => ({
                symbol: quote.symbol,
                price: quote.regularMarketPrice,
                change: quote.regularMarketChange,
                changePercent: quote.regularMarketChangePercent
            }));
        } else {
            return [{
                symbol: quotes.symbol,
                price: quotes.regularMarketPrice,
                change: quotes.regularMarketChange,
                changePercent: quotes.regularMarketChangePercent
            }];
        }
    } catch (error) {
        throw new Error(`Error fetching multiple stocks: ${error.message}`);
    }
}

// Export functions for use as module or command line
if (require.main === module) {
    // Run as standalone script
    const symbol = process.argv[2] || 'AAPL';
    
    getRealTimeStockInfo(symbol)
        .then(data => {
            console.log('\n=== Real-Time Stock Information ===');
            console.log(JSON.stringify(data, null, 2));
        })
        .catch(error => {
            console.error('Error:', error.message);
            process.exit(1);
        });
} else {
    // Export as module
    module.exports = {
        getRealTimeStockInfo,
        getStockHistory,
        getMultipleStocks
    };
}


