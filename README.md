# Pub-Sub Architecture Implementation

## Foreign Exchange Markets
Efficient liquid markets exist for exchanging one country's currency for another. For instance, exchanging USD 100 for British Pounds Sterling (GBP) at the rate of around USD 1.38 per GBP, and then exchanging those GBP 72.46 for Japanese Yen (JPY) at a rate of JPY 157.77 per GBP, followed by exchanging the obtained JPY 11432 back to USD at a rate of 114.34 yen for each USD, yields USD 100.02, resulting in an arbitrage opportunity. However, in real-world scenarios, transaction costs may reduce the profit.

## Price Feed
Assuming forex prices come from a single publisher, Forex Provider, who publishes prices in real-time using `UDP/IP` datagrams. Each message contains a series of 1 to 50 records in the following format:
<currency1, currency2, exchange rate, timestamp>

## Detecting Arbitrage
To detect arbitrage opportunities, we represent currency exchange rates as a graph, where nodes are currencies and edges represent trading markets. We manipulate edge weights to find negative-weight cycles using the Bellman-Ford algorithm, indicating arbitrage opportunities.

## Running the Subscriber
#### The subscriber:
- Subscribes to the forex publishing service.
- Updates a graph based on published prices.
- Runs Bellman-Ford.
- Reports any arbitrage opportunities.
- Assumes prices remain in force for 1.5 seconds or until superseded.

#### Steps 2 to 4 are repeated for ten minutes or until no messages are received for more than a minute.

## Guidance
- Use UDP/IP for communication.
- Utilize provided scripts for publishing and subscribing.
- Implement Bellman-Ford for path traversal.
