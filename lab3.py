"""
CPSC 5520, Seattle University
This is free and unencumbered software released into the public domain.
:Authors: Aditya Ganti
:Assignment: Lab 3
"""
from bellman_ford import BellmanFord
import datetime
import fxp_bytes_subscriber
import math
import socket
import sys


class Lab3:
    """
    Represents a subscriber for the Forex Provider class. It connects and registers with the publisher,
    and then proceeds to detect and print out an arbitrage.
    """
    SUBSCRIBER_HOST = 'localhost'
    SUBSCRIBER_PORT = 0

    def __init__(self, pub_host: str, pub_port: int):
        # Create a UDP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind the socket to a specified address and random port number
        # Since we're only running the subscription for one period, I'm not fixing
        # the port number for the subscriber to be running at.
        self.server_socket.bind(('localhost', 0))
        self.SUBSCRIBER_PORT = self.server_socket.getsockname()[1]
        print(f"\nSubscriber's UDP server listening on {self.SUBSCRIBER_HOST} : {self.SUBSCRIBER_PORT}\n")

        # Create an instance of the BellmanFord class
        self.bf = BellmanFord()

        # Create a dict to keep track of quote updates
        self.last_updated_quotes = {}

        # Variable to track UTC time offset
        self.offset_time = None

        # Send the listening address to the publisher
        self.connect_to_publisher(pub_host, pub_port)

        # Start the UDP listening server
        self.udp_server()

    def connect_to_publisher(self, pub_host: str, pub_port: int) -> None:
        """
        This function is responsible for subscribing to the Forex Provider publisher, and sending the subscriber's
        listening address to the publisher for further message consumption.

        :param pub_host: The publisher's hostname/IP address
        :param pub_port: The publisher's port number
        :return: None
        """
        # Create a socket object to connect to the publisher
        connect_to_pub_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connecting to the Forex Provider Publisher
            connect_to_pub_socket.connect((pub_host, pub_port))
            connect_to_pub_socket.sendall(fxp_bytes_subscriber.serialize_address(self.SUBSCRIBER_HOST, self.SUBSCRIBER_PORT))
        except Exception as e:
            print("Error: {}".format(e))
        finally:
            # Close the socket
            connect_to_pub_socket.close()

    @staticmethod
    def to_negative_log(edge_weight: float) -> float:
        """
        Calculate the negative logarithm of a given number.

        :param edge_weight: Input number
        :return: Negative logarithm of the input number
        """
        # Check if the input is non-positive, logarithm of non-positive number is undefined
        if edge_weight <= 0:
            raise ValueError("Number must be positive for logarithm generation. Please check the price being passed")

        # Return the negative logarithm
        return -math.log10(edge_weight)

    def print_graph(self) -> None:
        """
        Helper function to print the vertices and edges in the graph created by bellman_ford.py
        Prints the edges in a slightly more readable format

        :return: None
        """
        print("Vertices:", self.bf.vertices)
        print("Edges:")
        for from_vertex in self.bf.edges:
            for to_vertex, weight in self.bf.edges[from_vertex].items():
                print(f"{from_vertex} -> {to_vertex}: {weight}")

    @staticmethod
    def cross_to_currency_pair(cross: str) -> tuple:
        """
        Splits a cross into its 2 respective currencies

        :param cross: A string of the form "USDINR"
        :return: A tuple containing the currency pair of the form ("USD", "INR")
        """
        return cross[0:3], cross[3:]

    def is_delayed_message(self, cross: str, timestamp: datetime) -> bool:
        """
        Helper function to check whether a quote with a particular timestamp has arrived out-of-order

        :param cross: A string of the form "USDINR"
        :param timestamp: A datetime that represents the timestamp associated with an incoming quote
        :return: True if the message has a timestamp that dates it older than the current timestamp associated with
                    that particular currency pair
        """
        if self.cross_to_currency_pair(cross) in self.last_updated_quotes.keys():
            if self.last_updated_quotes[self.cross_to_currency_pair(cross)] > timestamp:
                return True
            else:
                self.last_updated_quotes[self.cross_to_currency_pair(cross)] = timestamp
                return False
        else:
            self.last_updated_quotes.update({self.cross_to_currency_pair(cross): timestamp})
            return False

    def remove_stale_messages(self) -> None:
        """
        If a particular exchange quote hasn't been updated in the last 1.5 seconds, remove the edge between that
        currency pair from the graph.

        :return: None
        """
        for currency_pair in list(self.last_updated_quotes.keys()).copy():
            if (datetime.datetime.utcnow() - self.last_updated_quotes[currency_pair]).total_seconds() > 1.5:
                print(f"Removing stale quote for {currency_pair}")
                del self.last_updated_quotes[currency_pair]
                self.bf.remove_edge(currency_pair[0], currency_pair[1])
                self.bf.remove_edge(currency_pair[1], currency_pair[0])

    def pretty_print(self, quote: dict) -> None:
        """
        Helper function to print incoming quotes to the terminal in a more readable format.
        All the quote prices are rounded off to 5 decimal places, for consistency.

        :param quote: A dict of the exchange quote received from the publisher
        :return: None
        """
        currency1, currency2 = self.cross_to_currency_pair(quote['cross'])
        price = quote['price']
        timestamp = quote['timestamp']
        print(f"{timestamp} --> {currency1} to {currency2} at {round(price, 5)}")

    def print_arbitrage(self, final_currency: str, predecessor: dict) -> None:
        """
        Prints the arbitrage opportunity that exists in the current scenario, keeping track of all the currencies and
        their exchange rates. Leverages the bellman_ford.py helper file for generating and keeping track of the graphical
        representation of all the currencies and their respective exchange rates.

        :param final_currency: The currency node at which the Bellman Ford algorithm detects a cycle
        :param predecessor: The dict that contains the predecessor nodes for each node in the cycle path
        :return: None
        """
        current_currency = final_currency
        arbitrage_exchanges = ["USD", current_currency]
        while predecessor[current_currency] is not None:
            arbitrage_exchanges.append(predecessor[current_currency])
            current_currency = predecessor[current_currency]
            # Accounting for infinite loops introduced into the graph
            if len(arbitrage_exchanges) > 11:
                return
        arbitrage_exchanges.reverse()

        print("\nARBITRAGE:")
        print("\tStart with USD 100")
        exchange_amount = 100
        for i in range(len(arbitrage_exchanges) - 1):
            current_currency = arbitrage_exchanges[i]
            exchange_currency = arbitrage_exchanges[i + 1]
            exchange_value = math.pow(math.e, -1 * self.bf.edges[current_currency][exchange_currency])
            exchange_amount *= exchange_value
            print(f"\tExchange {current_currency} for {exchange_currency} at {exchange_value} --> {exchange_currency} {exchange_amount}")

    def udp_server(self) -> None:
        """
        Starts the listening server for the subscriber based on the listening address provided via the console.
        Once the server subscribes to the forex provider, it processes all the incoming quotes.

        :return: None
        """
        while True:
            # Receive message and address from the client
            message, address = self.server_socket.recvfrom(1024)

            # Decode the received message (assuming it's a string)
            quotes = fxp_bytes_subscriber.unmarshal_message(message)

            for quote in quotes:
                self.pretty_print(quote)
                if self.is_delayed_message(quote['cross'], quote['timestamp']):
                    print("^^^ Ignoring the above message, since it has arrived out-of-sequence ^^^\n")
                    continue
                self.bf.add_edge(from_vertex=quote['cross'][0:3], to_vertex=quote['cross'][3:], weight=self.to_negative_log(quote['price']))
                self.bf.add_edge(from_vertex=quote['cross'][3:], to_vertex=quote['cross'][0:3], weight=self.to_negative_log(1/quote['price']))
            self.remove_stale_messages()

            distance, predecessor, negative_cycle = self.bf.shortest_paths('USD', tolerance=0.00001)
            if negative_cycle:
                self.print_arbitrage(negative_cycle[0], predecessor)


if __name__ == "__main__":
    """
    The entry point for the subscriber in the forex_provider pub-sub model. Parses command-line arguments,
    initializes a Lab3 instance, and starts the system with the provided parameters.

    Usage: python lab3.py PUBLISHER_HOST PUBLISHER_PORT
    
    :param sys.argv (list): Command-line arguments provided when running the script.
    :raises SystemExit: Exits the program if the correct number of arguments is not provided.
    """
    if len(sys.argv) != 3:
        print("Usage: python lab3.py PUBLISHER_HOST PUBLISHER_PORT")
        exit(1)
    Lab3(sys.argv[1], int(sys.argv[2]))
