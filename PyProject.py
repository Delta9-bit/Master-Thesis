import pandas as pd
import numpy as np
from numpy.random import seed
from sklearn import svm
from sklearn.model_selection import GridSearchCV
import matplotlib.pyplot as plt
import datetime as dt
import pandas_datareader as web
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from keras.layers import LSTM
from keras import Sequential
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
from sklearn.preprocessing import OneHotEncoder
import statsmodels.api as sm
from sklearn.preprocessing import MinMaxScaler
import math

# Display options
pd.set_option("display.max_rows", None, "display.max_columns", None)

#seed
seed(100)
tf.random.set_seed(100)

#computes indicators
def indicators(data):

    # Relative Strength Index
    def RSI(data, n):
        rsi = []

        for p in range (n, len(data)):
            h = []
            b = []

            for i in range(0, n):
                diff = 100 * ((data['Adj Close'][(p - n + i) + 1] - data['Adj Close'][p - n + i]) / data['Adj Close'][p - n + i])

                if diff < 0:
                    b.append(abs(diff))
                elif diff > 0:
                    h.append(diff)

            u = (1 / (n + 1)) * sum(h)
            d = (1 / (n + 1)) * sum(b)

            rsi.append(100 - (100 / (1 + (u / d))))

        return rsi


    # Stochastic Oscillator
    def oscill(data, n, d):
        K = []
        ma = []

        for p in range(n, len(data)):
            values = []
            close = data['Adj Close'][p]

            for i in range(p - n, p + 1):
                values.append(data['Adj Close'][i])

            high = max(values)
            low = min(values)

            K.append(((close - low) / (high - low)) * 100)

        for p in range(d, len(K)):
            sum = 0

            for i in range(p - d, p + 1):
                sum = sum + K[i]
                Kma = (1 / d) * sum

            ma.append(Kma)

        return K, ma;


    # Bollinger Bands
    def boll(data, k, n):
        MA = []
        boll_up = []
        boll_dw = []

        for p in range(n, len(data)):
            sum = 0
            var = 0

            for i in range(p - n, p + 1):
                sum = sum + data['Adj Close'][i]

            ma = (1 / (n + 1)) * sum

            for i in range(p - n, p + 1):
                spread = (data['Adj Close'][i] - ma) ** 2
                var = var + spread

            sigma = np.sqrt((1 / (n + 1)) * var)

            up = ma + (k * sigma)
            dw = ma - (k * sigma)

            MA.append(ma)
            boll_up.append(up)
            boll_dw.append(dw)

        return MA, boll_up, boll_dw;


    # Moving Average Convergence Divergence
    def MACD(data, n_large, n_small):
        list_small = []
        list_large = []
        ma_small = []
        ma_large = []

        for p in range(n_small, len(data)):
            for i in range(p - n_small, p):
                list_small.append(data['Adj Close'][i])

            small = (1 / (n_small + 1)) * sum(list_small)
            ma_small.append(small)

        for p in range(n_large, len(data)):
            for i in range(p - n_large, p):
                list_large.append(data['Adj Close'][i])

            large = (1 / (n_small + 1)) * sum(list_large)
            ma_large.append(large)

        return ma_small, ma_large;


    # Average Directional Index
    def ADX(data, n):

        true_range = [0]

        for p in range(1, len(data)):
            rnge = []

            high_low = abs(data['High'][p] - data['Low'][p])
            rnge.append(high_low)
            high_close = abs(data['High'][p] - data['Adj Close'][p - 1])
            rnge.append(high_close)
            low_close = abs(data['Low'][p] - data['Adj Close'][p - 1])
            rnge.append(low_close)

            true_range.append(max(rnge))

            if true_range[p] == 0:
                true_range[p] = true_range[p - 1]

        DM_plus = []
        DM_minus = []

        for p in range(0, len(data)):
            if (data['High'][p] - data['High'][p - 1]) >  (data['Low'][p - 1] - data['Low'][p]):
                DM_plus.append((data['High'][p] - data['High'][p - 1]))
                DM_minus.append(0)
            else:
                DM_minus.append((data['Low'][p - 1] - data['Low'][p]))
                DM_plus.append(0)

        rnge = 0
        minus = 0
        plus = 0

        for p in range(0, n):
            rnge = rnge + true_range[p]
            minus = minus + DM_minus[p]
            plus = plus + DM_plus[p]

        smooth_range = []
        smooth_plus = []
        smooth_minus = []

        for p in range(0, n):
            smooth_range.append(0)
            smooth_plus.append(0)
            smooth_minus.append(0)

        smooth_range.append(rnge)
        smooth_plus.append(plus)
        smooth_minus.append(minus)

        for p in range(n + 1, len(data)):
            avg_range = smooth_range[p - 1] / n
            avg_minus = smooth_minus[p - 1] / n
            avg_plus = smooth_plus[p - 1]/ n

            smooth_range.append(smooth_range[p - 1] - avg_range + true_range[p])
            smooth_minus.append(smooth_minus[p - 1] - avg_minus + DM_minus[p])
            smooth_plus.append(smooth_plus[p - 1] - avg_plus + DM_plus[p])

        indicator_plus = [0]
        indicator_minus = [0]

        for p in range(1, len(data)):
                indicator_plus.append((smooth_plus[p] / true_range[p]) * 100)
                indicator_minus.append((smooth_minus[p] / true_range[p]) * 100)

        dx = [0, 0, 0, 0, 0]

        for p in range(n, len(data)):
            dx.append((abs((indicator_plus[p] - indicator_minus[p]) / (indicator_plus[p] + indicator_minus[p]))) * 100)

        adx = []

        for p in range(0, len(data)):
            adx.append((1 / n) * sum(dx[p - n : p]))

        return adx;


    # On-Balance Volume
    def OBV(data):
        obv = [0]

        for p in range(1, len(data)):
            if data['Adj Close'][p] > data['Adj Close'][p - 1]:
                obv.append(obv[p - 1] + data['Volume'][p])
            elif data['Adj Close'][p] < data['Adj Close'][p - 1]:
                obv.append(obv[p - 1] - data['Volume'][p])
            else:
                obv.append(obv[p - 1])

        return obv;


    rsi = 9
    so = 14
    ma_so = 5
    ma = 20
    sd_boll = 2
    macd_small = 12
    macd_large = 26
    adx_length = 14

    RSI = RSI(data, rsi) # 9-days RSI
    K, D = oscill(data, so, ma_so) # 14-days SO & 5-days moving average
    MA, boll_up, boll_dw = boll(data, sd_boll, ma) # 20-days MA and 2-sd bollinger bands
    macd_short, macd_long = MACD(data, macd_large, macd_small) # 12 & 26 days moving averages
    adx = ADX(data, adx_length) # 14 days ADX & positive and negative indicators
    obv = OBV(data) # On Balance Volume

    # removing NAs
    RSI = RSI[(macd_large - rsi) : len(RSI)]
    K = K[(macd_large - so) : len(K)]
    D = D[(macd_large - (so + ma_so)) : len(D)]
    MA = MA[(macd_large - ma) : len(MA)]
    boll_up = boll_up[(macd_large - ma): len(boll_up)]
    boll_dw = boll_dw[(macd_large - ma): len(boll_dw)]
    macd_short = macd_short[(macd_large - macd_small) : len(macd_short)]
    adx = adx[macd_large : len(adx)]
    obv = obv[macd_large : len(obv)]

    df = {'RSI': RSI, 'D': D, 'MA': MA, 'boll_up': boll_up,
          'boll_dw': boll_dw, 'MACD_short' : macd_short, 'MACD_long' : macd_long,
          'adx' : adx, 'OBV' : obv}
    X = pd.DataFrame(df) # coercing indicators into dataframe

    return X
# encodes data into buy/hold/sell and add indicators
def encode(data):
    list = []

    for p in range(0, len(data) - 1):
        if data['Adj Close'][p + 1] > data['Adj Close'][p]:
            list.append(1)
        elif data['Adj Close'][p + 1] == data['Adj Close'][p]:
            list.append(2)
        elif data['Adj Close'][p + 1] < data['Adj Close'][p]:
            list.append(3)
        else:
            print('error')

    X = indicators(data)  # computes indicators

    data.drop(['High', 'Low', 'Open', 'Close', 'Volume'], axis = 1, inplace = True)

    data.drop(data.index[len(data) - 1], axis=0, inplace=True) #remove last observation where position is NA

    data.insert(1, 'position', list) # add position

    data.drop(data.index[0: (len(data) - len(X))], axis=0, inplace=True)  # remove first observations where indicators are NA
    X.reset_index(drop=True, inplace=True)
    data.reset_index(drop=True, inplace=True)  # reseting index in data and X before concat
    data = pd.concat([data, X], axis=1)  # add X

    return data;
# transform the indicators from raw value to signal
def transform(data):
    RSI_signal = [4]
    D_signal = [4]
    boll_signal = [2]
    MACD_signal = [2]

    for p in range(1, len(data)):
        if data['RSI'][p] > 70 and data['RSI'][p - 1] < 70:
            RSI_signal.append(0)
        elif data['RSI'][p] < 70 and data['RSI'][p - 1] > 70:
            RSI_signal.append(1)
        elif data['RSI'][p] > 30 and data['RSI'][p - 1] < 30:
            RSI_signal.append(2)
        elif data['RSI'][p] < 30 and data['RSI'][p - 1] > 30:
            RSI_signal.append(3)
        else:
            RSI_signal.append(4)

        if data['D'][p] > 80 and data['D'][p - 1] < 80:
            D_signal.append(0)
        elif data['D'][p] < 80 and data['D'][p - 1] > 80:
            D_signal.append(1)
        elif data['D'][p] > 20 and data['D'][p - 1] < 20:
            D_signal.append(2)
        elif data['D'][p] < 20 and data['D'][p - 1] > 20:
            D_signal.append(3)
        else:
            D_signal.append(4)

        if data['Adj Close'][p] > data['boll_up'][p]:
            boll_signal.append(0)
        elif data['Adj Close'][p] < data['boll_dw'][p]:
            boll_signal.append(1)
        else:
            boll_signal.append(2)

        if data['MACD_short'][p] > data['MACD_long'][p] and data['MACD_short'][p - 1] < data['MACD_long'][p - 1]:
            MACD_signal.append(0)
        elif data['MACD_short'][p] < data['MACD_long'][p] and data['MACD_short'][p - 1] > data['MACD_long'][p - 1]:
            MACD_signal.append(1)
        else:
            MACD_signal.append(2)

    for p in range(0, len(data)):
        if data['position'][p] == 2:
            data['position'][p] = 1
        elif data['position'][p] == 3:
            data['position'][p] = 0

    data['RSI'] = RSI_signal
    data['D'] = D_signal
    data['boll'] = boll_signal
    data['MACD'] = MACD_signal

    encoder = OneHotEncoder()

    RSI_cat = encoder.fit_transform(data[['RSI']]).toarray()
    RSI_name = encoder.get_feature_names(['RSI'])
    RSI_cat = pd.DataFrame(RSI_cat, columns=RSI_name)

    D_cat = encoder.fit_transform(data[['D']]).toarray()
    D_name = encoder.get_feature_names(['D'])
    D_cat = pd.DataFrame(D_cat, columns=D_name)

    boll_cat = encoder.fit_transform(data[['boll']]).toarray()
    boll_name = encoder.get_feature_names(['boll'])
    boll_cat = pd.DataFrame(boll_cat, columns=boll_name)

    MACD_cat = encoder.fit_transform(data[['MACD']]).toarray()
    MACD_name = encoder.get_feature_names(['MACD'])
    MACD_cat = pd.DataFrame(MACD_cat, columns=MACD_name)

    data = data.join(RSI_cat)
    data = data.join(D_cat)
    data = data.join(boll_cat)
    data = data.join(MACD_cat)

    data.drop(['MACD_short', 'MA', 'boll_up', 'boll_dw', 'boll', 'MACD_long', 'RSI', 'D', 'MACD', 'RSI_4', 'D_4', 'boll_2'], axis = 1, inplace = True)

    return data;
# Splits data into training and testing
def test_train_split(data, train):

    slice = train * len(data)
    slice = int(slice) # slice = index where test set begins

    data_copy = data[data.index[0] : data.index[slice - 1]]
    data_test = data[data.index[slice] : data.index[len(data) - 1]] # slicing data
    data = data_copy

    data.reset_index(drop = True, inplace = True)
    data_test.reset_index(drop=True, inplace=True)

    y = data['position'] # re-creating X and y
    y.reset_index(drop = True, inplace =True)
    X = data.drop(['Adj Close', 'position'], axis = 1)
    X.reset_index(drop = True, inplace = True)

    y_test = data_test['position'] # creating X_test and y_test
    y_test.reset_index(drop=True, inplace=True)
    X_test = data_test.drop(['Adj Close', 'position'], axis = 1)
    X_test.reset_index(drop=True, inplace=True)

    return data, data_test, X, y, X_test, y_test;
def test_train_SP(data, train):
    data = data[data.index[26]: data.index[len(data) - 1]]

    data.reset_index(drop=True, inplace=True)

    slice = train * len(data)
    slice = int(slice)

    data_copy = data[data.index[0] : data.index[slice - 1]]
    data_test = data[data.index[slice] : data.index[len(data) - 1]]  # slicing data
    data = data_copy

    data_test.reset_index(drop = True, inplace = True)

    return data, data_test;
# plots of conditional distributions with respect to inputs
def inputPlots(data):
    fig, axs = plt.subplots(2, 3)

    axs[0, 0].scatter(y = data['RSI'], x = data['position'])
    axs[0, 0].set_title('Relative Strenght Index')
    axs[0, 0].set_xlabel('position')
    axs[0, 0].set_ylabel('RSI')

    axs[0, 1].scatter(y=data['MA'], x=data['position'])
    axs[0, 1].set_title('20 days moving average')
    axs[0, 1].set_xlabel('position')
    axs[0, 1].set_ylabel('moving average')

    axs[0, 2].scatter(y = data['D'], x = data['position'])
    axs[0, 2].set_title('smoothed stochastic oscillator')
    axs[0, 2].set_xlabel('position')
    axs[0, 2].set_ylabel('oscillator')

    axs[1, 0].scatter(y = data['adx'], x = data['position'])
    axs[1, 0].set_title('Average Directional Index')
    axs[1, 0].set_xlabel('position')
    axs[1, 0].set_ylabel('ADX')

    axs[1, 1].scatter(y = data['OBV'], x = data['position'])
    axs[1, 1].set_title('On-Balance Volume')
    axs[1, 1].set_xlabel('position')
    axs[1, 1].set_ylabel('OBV')

    axs[1, 2].scatter(y = data['boll_up'], x = data['position'])
    axs[1, 2].set_title('Upper Bollinger Band')
    axs[1, 2].set_xlabel('position')
    axs[1, 2].set_ylabel('Bollinger Band')

    fig.subplots_adjust(hspace=0.5, wspace=0.5)

    plt.show()
# Neural net architecture
def NeuralNet():
        NN = Sequential()

        NN.add(layers.Dense(10, activation='relu'))
        NN.add(layers.Dense(10, activation='relu'))
        NN.add(layers.Dense(2, activation='softmax'))

        NN.compile(optimizer='adam',
                   loss=keras.losses.SparseCategoricalCrossentropy(),
                   metrics=keras.metrics.SparseCategoricalCrossentropy(),
                   )

        NN._name = 'Neural_Network'

        return NN
# AUC + ROC + confusion matrix (in case of binary buy/sell classification)
def results(y, pred_class, model, ticker):
    fig, axs  = plt.subplots(1, 2, figsize = (10, 5))

    fpr, tpr, thr = roc_curve(y, pred_class)
    roc_auc = auc(fpr, tpr)
    print(model, roc_auc)

    axs[0].plot(fpr, tpr, lw=2, alpha=0.7, label=model)
    axs[0].plot([0, 1], [0, 1], linestyle='--', lw=2, color='r', alpha=.8)
    axs[0].set_xlabel('False Positive Rate')
    axs[0].set_ylabel('True Positive Rate')
    axs[0].set_title(ticker)

    axs[1].plot(history.history['loss'])
    axs[1].set_xlabel('Epochs')
    axs[1].set_ylabel('Loss')

    conf_mat = confusion_matrix(pred_class, y)
    report = classification_report(pred_class, y)
    print(report, conf_mat)
# ROC curve + confusion matrix
def roc(y, pred_class, model, ticker, model_name):
    fpr, tpr, thr = roc_curve(y, pred_class)
    roc_auc = auc(fpr, tpr)
    print(model, roc_auc)

    plt.plot(fpr, tpr, lw=2, alpha=0.7, label=model_name)
    plt.plot([0, 1], [0, 1], linestyle='--', lw=2, color='r', alpha=.8)
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(ticker)
    plt.legend()
    plt.show()

    conf_mat = confusion_matrix(pred_class, y)
    report = classification_report(pred_class, y)
    print(report, conf_mat)
# learning curve
def learning_curve(model, ticker):
    plt.plot(history.history['loss'])
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title(ticker)
# Second Neural Net architecture
def ImprovedNeuralNet():
        NN = Sequential()

        NN.add(layers.Dense(32, activation='relu'))
        NN.add(layers.Dense(32, activation='relu'))
        NN.add(layers.Dense(32, activation='relu'))
        NN.add(layers.Dense(1, activation='sigmoid'))

        NN.compile(optimizer='adam',
                   loss=keras.losses.BinaryCrossentropy(),
                   metrics=keras.metrics.BinaryCrossentropy(),
                   )

        NN._name = 'Improved_Neural_Net'

        return NN
# Encodes predictions into string variables easier to read (deprecated)
def output_encode(pred_class, data):
    list = []

    for p in range(0, len(pred_class)):
        if pred_class[p] == 1:
            list.append('buy')
        elif pred_class[p] == 0:
            list.append('sell')


    data.insert(3, 'pred_string', list)
    data.insert(4, 'pred_pos', pred_class)

    return data
# Computes profits based on predictions and returns for the S&P500 same period
def profits_SP(data, amount):
    init = amount
    profits = []
    total = [amount]
    returns = []
    realized_profits = []
    realized_returns = []

    for p in range(0, len(data) - 1):

        #tx = (data['Adj Close'][p + 1] - data['Adj Close'][p]) / data['Adj Close'][p]
        tx = math.log(data['Adj Close'][p + 1]) - math.log(data['Adj Close'][p])

        if tx > 0:
            profit = init * tx
            init = init + profit
            if init > amount:
                realized_profits.append(init - amount)
                realized_returns.append(tx)
                init = amount
            else:
                realized_profits.append(0)
                realized_returns.append(0)
        else:
            profit = init * tx
            init = init + profit
            realized_profits.append(0)
            realized_returns.append(0)

        profits.append(profit)

        total.append(init)

        returns.append(tx)

    profits.append(0)
    returns.append(0)
    realized_profits.append(0)
    realized_returns.append(0)

    backtest = {'Close Price' : data['Adj Close'],
                '%return' : returns,
                'profits' : profits,
                'realized_profits' : realized_profits,
                'realized_returns': realized_returns}

    backtest = pd.DataFrame(backtest)

    data['profit'] = profits
    data['total'] = total
    data['%returns'] = returns
    data['realized_profits'] = realized_profits
    data['realized_returns'] = realized_returns

    sum_returns = sum(data['%returns'])
    sum_profits = sum(data['profit'])
    sum_realized_profits = sum(data['realized_profits'])
    percentage_gain = (sum_realized_profits * 100) / amount

    print('sum profits : ', round(sum_profits, 2))
    print('sum returns : ', round(sum_returns, 2))
    print('sum realized returns : ', round(sum_realized_profits, 2))
    print('total realized return : ', round(percentage_gain, 2), '%')  # sum profits and compute % return

    return data;
def profits(data, amount):
    available = amount
    total = 0
    profit = 0
    realized_returns = []
    realized_profits = []
    returns = []
    available_amount = []
    invested_amount = []
    profits = []

    for p in range(0, len(data) - 1):

        #rate = (data['Adj Close'][p + 1] - data['Adj Close'][p]) / data['Adj Close'][p]
        rate = math.log(data['Adj Close'][p + 1]) - math.log(data['Adj Close'][p])
        returns.append(rate)

        if data['pred'][p] == 0:
            if p > 0:
                available = total
            profit = 0
            realized_returns.append(0)
            profits.append(profit)
            available_amount.append(available)
            invested_amount.append(0)
        else:
            if total == 0:
                total = available
            else:
                total = total

            available = 0
            profit = total * rate
            total = total + profit
            realized_returns.append(rate)
            profits.append(profit)
            available_amount.append(available)
            invested_amount.append(total)

        if total > amount:
            realized_profits.append(total - amount)
            total = amount
        else:
            realized_profits.append(0)
            total = total

    profits.append(0)
    returns.append(0)
    realized_profits.append(0)
    realized_returns.append(0)
    invested_amount.append(0)
    available_amount.append(total)

    backtest = {'Close Price' : data['Adj Close'],
                '%return' : returns,
                'position' : data['position'],
                'pred' : data['pred'],
                'profits' : profits,
                'available' : available_amount,
                'invested' : invested_amount,
                'realized_profits' : realized_profits,
                'realized_returns': realized_returns}

    backtest = pd.DataFrame(backtest)

    data['available'] = available_amount
    data['invested'] = invested_amount
    data['%returns'] = returns
    data['profit'] = profits
    data['realized_profits'] = realized_profits
    data['realized_returns'] = realized_returns

    sum_returns = sum(data['%returns'])
    sum_profits = sum(data['profit'])
    sum_realized_profits = sum(data['realized_profits'])
    percentage_gain = (sum_realized_profits * 100) / amount

    print('sum profits : ', round(sum_profits, 2))
    print('sum returns : ', round(sum_returns, 2))
    print('sum realized returns : ', round(sum_realized_profits, 2))
    print('total realized return', round(percentage_gain, 2), '%')  # sum profits and compute % return

    return backtest;
# Counts the number of time the model is right/wrong
def accuracy(data):
    proportion = []

    for p in range(0, len(data) - 1):

        tx = (data['Adj Close'][p + 1] - data['Adj Close'][p]) / data['Adj Close'][p]

        if data['position'][p] == data['pred'][p]:
            proportion.append(1)
        else:
            proportion.append(0)

    proportion.append(0)

    data['proportion'] = proportion

    return data;
# Sharpe ratio
def sharpe(data, market_data):
    returns = data['realized_returns']
    market_returns = market_data['%returns']

    length_period = len(data['realized_returns'])

    volatility = np.std(returns) ** (250 / length_period)
    market_volatility = np.std(market_returns) ** (250 / length_period)

    expected_return = ((sum(returns) + 1) ** (250 / length_period)) - 1
    expected_market_return = ((sum(market_returns) + 1) ** (250 / length_period)) - 1

    ratio = expected_return / volatility
    market_ratio = expected_market_return / market_volatility

    print("E[R_m]: ", round(expected_market_return, 2))
    print("E[R_i]: ", round(expected_return, 2))
    print("Volatility market: ", round(market_volatility, 2))
    print("Volatility asset: ", round(volatility, 2))
    print("Sharpe market: ", round(market_ratio, 2))
    print("Sharpe asset: ", round(ratio, 2))
# Sortino ratio
def sortino(data, market_data, T):
    down = []
    down_market = []
    market_returns = market_data['%returns']
    returns = data['realized_returns']
    length_period = len(market_data)

    for p in range(0, length_period):
        if data['realized_returns'][p] < T:
            down.append(data['realized_returns'][p])
        if market_data['%returns'][p] < T:
            down_market.append(market_data['%returns'][p])

    semi_dev = np.std(down) ** (250 / length_period)
    market_semi_dev = np.std(down_market) ** (250 / length_period)

    expected_return = ((sum(returns) + 1) ** (250 / length_period)) - 1
    expected_market_return = ((sum(market_returns) + 1) ** (250 / length_period)) - 1

    ratio = expected_return / semi_dev
    market_ratio = expected_market_return / market_semi_dev

    print("sigma down asset: ", round(semi_dev, 2))
    print("sigma down market: ", round(market_semi_dev, 2))
    print("sortino asset: ", round(ratio, 2))
    print("sortino market: ", round(market_ratio, 2))

# Choosing assets
ticker = 'AF.PA' #Walmart:WMT - Apple:AAPL - AirFrance:AF.PA - Tesla:TSLA
ticker_SP = '^GSPC' # ticker for the S&P500

start = dt.datetime(2010,8,1) # series starts on 2010/08/01
end = dt.datetime(2019,12,31) # ends on 2019/12/31

# importing data from yahoo API
data = web.DataReader(ticker, 'yahoo', start, end)
data_SP = web.DataReader(ticker_SP, 'yahoo', start, end)

# plot of the serie
plt.plot(data['Adj Close'])
plt.show()
plt.title(ticker)
plt.ylabel('Adj Close')
plt.xlabel('Time')

data = encode(data) # encodes data into buy/hold/sell and add indicators

data = transform(data) # transform the indicators from raw value to signal

train_size = 0.7 # 70% of the data to training 30% to testing

# Spliting data into training and testing sets
data, data_test, X, y, X_test, y_test = test_train_split(data, train_size)
data_SP, data_SP_test = test_train_SP(data_SP, train_size)

# position frequencies (test VS train)
plt.bar(data['position'].value_counts().index, data['position'].value_counts().values)
plt.bar(data_test['position'].value_counts().index, data_test['position'].value_counts().values)
plt.title(ticker)
plt.show()

inputPlots(data) # plots of conditional distributions with respect to inputs

# Logit
logit = sm.MNLogit(y, X)
logit_fit = logit.fit(method = 'newton', maxiter = 100)
logit_fit.summary()

#Normalize features
scaler = MinMaxScaler(feature_range = [0, 1]).fit(X)
X = scaler.transform(X) # Train data

scaler = MinMaxScaler(feature_range = [0, 1]).fit(X_test)
X_test = scaler.transform(X_test) # Test data

# Standard Neural Net
NN = NeuralNet() # creates Neural Net
history = NN.fit(X, y, epochs = 500) # fits the model
pred = NN.predict(X) # Predicted probabilities on train data
pred_class = pred.argmax(axis = -1) # Predicted class on train data
pred_proba =  NN.predict_proba(X)[:, 1] # computes predicted probabilities for each class
pred_class_test = NN.predict_classes(X_test)

roc(y, pred_class, NN, ticker, 'Neural Network') # ROC + confusion matrix train data
roc(y_test, pred_class_test, NN, ticker, 'Neural Network') # ROC + confusion matrix test data
learning_curve(NN, ticker) # learning cruve

data_test['pred'] = pred_class_test # adding predictions as 0/1 to the dataframe
data_test = accuracy(data_test) # Counts the number of time the model is right/wrong

# Improved Neural Net
ImprovNN = ImprovedNeuralNet() # creates Neural Net
history = ImprovNN.fit(X, y, epochs = 1000) # fits the model
pred = ImprovNN.predict(X) # Predicted probabilities on train data
pred_class = ImprovNN.predict_classes(X) # Predicted class on train data
pred_class_test = ImprovNN.predict_classes(X_test) # Predicted class on test data

roc(y, pred_class,ImprovNN, ticker, 'Improved Neural Network') # ROC + confusion matrix train data
roc(y_test, pred_class_test,ImprovNN, ticker, 'Improved Neural Network') # ROC + confusion matrix test data
learning_curve(ImprovNN, ticker) # learning cruve

data_test['pred'] = pred_class_test # adding predictions as 0/1 to the dataframe
data_test = accuracy(data_test) # Counts the number of time the model is right/wrong

# linear SVM
SVM = svm.SVC()
SVM_fit = SVM.fit(X, y)
pred_class = SVM.predict(X)
pred_class_test = SVM.predict(X_test)

roc(y, pred_class, SVM, ticker, 'linear SVM') # ROC + confusion matrix train data
roc(y_test, pred_class_test, SVM, ticker, 'linear SVM') # ROC + confusion matrix test data
learning_curve(SVM, ticker) # learning cruve

data_test['pred'] = pred_class_test # adding predictions as 0/1 to the dataframe
data_test = accuracy(data_test) # Counts the number of time the model is right/wrong

# RBF kernel SVM
grid = {
	'C': [0.001, 0.01, 0.1, 1, 10, 100],
	'gamma': [10, 1, 0.1, 0.01, 0.001, 0.0001, 0.00001],
	'kernel': ['rbf']} # grid of values to evaluate

rbf_SVM = svm.SVC(max_iter = 1000)
grid_search = GridSearchCV(rbf_SVM, param_grid = grid, refit = True)
rbf_SVM_fit = grid_search.fit(X, y)
pred_class = grid_search.predict(X)
pred_class_test = grid_search.predict(X_test)

print(grid_search.best_params_) # displays the best set of parameters

roc(y, pred_class, grid_search, ticker, 'Kernel SVM') # ROC + confusion matrix train data
roc(y_test, pred_class_test, grid_search, ticker, 'Kernel SVM') # ROC + confusion matrix test data
learning_curve(rbf_SVM, ticker) # learning curve

data_test['pred'] = pred_class_test # adding predictions as 0/1 to the dataframe
data_test = accuracy(data_test) # Counts the number of time the model is right/wrong

# Profits
amount = 1000

backtest = profits(data_test, amount) # computes profits made with specified initial investment
backtest_SP = profits_SP(data_SP_test, amount) # same for S&P

sharpe(backtest, backtest_SP)
sortino(backtest, backtest_SP, 0)

# benchmark profits
backtest_bench = profits_SP(data_test, amount)

sharpe(backtest, backtest_bench)
sortino(backtest, backtest_bench, 0)

plt.plot(data_test['profit'])
plt.show
plt.plot(data_test['realized_profits'])
plt.show()

#LSTM
def lstm():
    for p in range(0, len(data)):
        if data['position'][p] == 2:
            data['position'][p] = 1
        elif data['position'][p] == 3:
            data['position'][p] = 0

    scaler = MinMaxScaler(feature_range = [0, 1]).fit(X)
    X = scaler.transform(X)

    n = 14
    Xtrain = []
    ytrain = []

    for p in range(n, len(X)):
        Xtrain.append(X[p - n : p, : X.shape[1]])
        ytrain.append(y[p])

    Xtrain, ytrain = (np.array(Xtrain), np.array(ytrain))
    Xtrain = np.reshape(Xtrain, (Xtrain.shape[0], Xtrain.shape[1], Xtrain.shape[2]))


    def lstm_net():
        model = Sequential()
        model.add(LSTM(64, input_shape = (Xtrain.shape[1], Xtrain.shape[2])))
        model.add(layers.Dense(1))

        model.compile(loss = keras.losses.BinaryCrossentropy(),
                    metrics=keras.metrics.BinaryCrossentropy(),
                    optimizer="adam")

        return model


    lstm = lstm_net()

    history = lstm.fit(Xtrain, ytrain, epochs = 100)

    pred = lstm.predict(Xtrain) # Predicted probabilities on train data
    pred_class = pred.argmax(axis = -1) # Predicted class on train data

    results(ytrain, pred_class, lstm)



