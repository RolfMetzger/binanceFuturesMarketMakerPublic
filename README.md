Binance Futures Market Maker, by Jarett Dunn


Support this open-source project organically, without subscription! Sign up to Binance here using this referral link: https://www.binance.com/en/register?ref=VZJQV7PR and for futures here: https://www.binance.com/en/futures/ref/neomenia


Support this open-source project! $1 or $5 a month from a crowd adds up! https://github.com/sponsors/dunncreativess


Setup:


1. Clone or download repo
2. cd into dir
3. python3 setup.py install
4. create a file called config.json that looks like this:


{"binApi": "",
	"binSecret": "",
	"RISK_CHARGE_VOL": {"current": 0.05, "max": 5, "step": 0.05, "min": 0.05}, "VOL_PRIOR": {"current": 10, "max": 500, "step": 10, "min": 10}, "EWMA_WGT_COV": {"current": 0.05, "max": 4, "step": 0.05, "min": 0.05}}


The 'current' values here are your input variables to optimize the bot.


The first variable I would prioritize is RISK_CHARGE_VOL which dictates how wide markets should be in response to volatility (in whatever manner it is projected - in the case of the sample code, an EWMA process).



EWMA_WGT_COV would be the next one I think because it directly affects the volatility forecast and it is generally not clear how "fast-moving" the EWMA vol forecast should be.



After that, VOL_PRIOR because that sets the starting point for your vol estimation. You may want to adjust the code so that instead of VOL_PRIOR being a constant (essentially), it is determined by e.g. some historical vol estimate. VOL_PRIOR only really matters that much when the bot has been started or restarted.



For our competition run, Coindex Labs is optimizing these input variables using our proprietary AI. Note that the defaults here will probably lose funds, they're not optimized or recommended.



binApi is your api key (futures enabled...)


binSecret is your api secret...


5. python3 market_maker.py
6. fun and profit!


https://hackernoon.com/porting-a-bot-to-binance-futures-market-making-competition-6v6a31qh


Track our bot's delta in real-time (after the test bot's run is complete) here: http://coindexbot.duckdns.org


Original README.md as follows:


Sample market maker bot
===

Strategy
---

The bot layers bids and offers around the market mid, which it attempts to calculate from the order book. The spread between quoted bids and offers is determined by a user-set risk charge on volatility. Volatility is estimated by an EWMA (Exponentially Weighted Moving Average Process) with frequency and parameters that may also be set by the user.

Set up
---

This bot requires python3 and the [Deribit api wrapper](https://pypi.org/project/deribit_api/).

To set up the bot, edit the `KEY` and `SECRET` variables in the code to your credentials. You can obtain those from the [Deribit account](https://www.deribit.com/main#/account?scrollTo=api).

To start the bot, run `python3 market_maker.py`.

Disclaimer
---

Different market conditions will produce different results. This code is for sample purposes only. It comes as is, with no warranty or guarantee of performance.
