import sys
from amznbot import AmznBot
from website import Website


def main():
    # increase default recursion limit set by Python.
    sys.setrecursionlimit(10 ** 6)

    response1 = user_response(
        "Which website do you want to scrape (amazon.de/ amazon.co.uk):\t",
        ["amazon.de", "amazon.co.uk"],
    )

    # response2 = user_response(
    #     "Include Amazon Warehouse Deals (experimental feature) (y/n):\t", ["y", "n"]
    # )

    include_whd = False
    # if response2 == "y":
    #     include_whd = True
    # elif response2 == "n":
    #     include_whd = False

    AmznBot(Website(response1), include_whd).run()


def user_response(msg, response_options):
    response = input(msg)

    for option in response_options:
        if str(response) == option:
            return str(response)

    print("Please enter a valid argument.")
    user_response(msg, response_options)


main()
