import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy import stats
import seaborn
import statsmodels.formula.api as sm
import tabulate
from statsmodels.api import add_constant
from sklearn.ensemble import RandomForestRegressor
from treeinterpreter import treeinterpreter as ti
from sklearn.cross_validation import StratifiedKFold
from sklearn.cross_validation import cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn import metrics
# from sklearn.neural_network import MLPClassifier
# from sknn.mlp import Classifier, Layer
import pybrain as pb
from pybrain.datasets            import ClassificationDataSet
from pybrain.utilities           import percentError
from pybrain.tools.shortcuts     import buildNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.structure.modules   import SoftmaxLayer
from pybrain.datasets 			 import SupervisedDataSet
from sklearn.svm 				 import SVR
from patsy                       import dmatrix


def Fed_SSI(married, countable_income, deemed_income):
	if married !='None or children':
		SSI = 1100 * 12
		if (SSI - countable_income - deemed_income) < 0:
			return 0
		else:
		#use 1100 as Federal SSI amount
			SSI -= countable_income
			SSI -= deemed_income
			return SSI/2.

	else:
		#use 733 as Federal SSI amount
		SSI = 733 * 12
		if (SSI - countable_income - deemed_income) < 0:
			return 0
		else:
			SSI -= countable_income
			SSI -= deemed_income
			return SSI

def countable(earned_income, unearned_income):
	SSI_countable = earned_income + unearned_income

	#Allowing only positive values
	SSI_countable = np.where(SSI_countable > 0, SSI_countable, 0)
	# Taking $20 out of most income
	SSI_countable = np.where(SSI_countable > 20 * 12, SSI_countable - 20 *12, 0)
	#Case where unearned income < 20 *12 and earned income + unearned income - 20 * 12 <= 65 * 12
	SSI_countable = np.where((SSI_countable < 65 * 12) & (earned_income >= 65 * 12), 0, SSI_countable)
	#Case where unearned income < 20 * 12, earned income < 65 * 12 but countable income > earned income
	SSI_countable = np.where((SSI_countable < 65 * 12) & (earned_income < 65 * 12) & (SSI_countable > earned_income),  SSI_countable - earned_income, SSI_countable)
	#Case where unearned income < 20 *12, earned income < 65 *12 and countable < earned income
	SSI_countable = np.where((SSI_countable < 65 * 12) & (earned_income < 65 * 12) & (SSI_countable <= earned_income), 0, SSI_countable)
	#Case where unearned income > 20*12 and earned income < 65 * 12
	SSI_countable = np.where((SSI_countable >= 65 * 12) & (earned_income < 65 * 12), SSI_countable - earned_income, SSI_countable)
	#Case where countable is greater than 65 * 12
	SSI_countable = np.where((SSI_countable >= 65 * 12) & (earned_income >= 65 * 12), SSI_countable - 65 * 12, SSI_countable)

	# Taking out half of what's left of earnings
	#Accounting for when the initial $20 is taken out of earned income
	SSI_countable = np.where((earned_income > 65 * 12) & (SSI_countable > 0) & (unearned_income < 20 * 12), SSI_countable - 0.5*(earned_income - (20 * 12 - unearned_income) - 65 * 12), SSI_countable)
    # Case when all initial $20 is taken from unearned income
	SSI_countable = np.where((earned_income > 65 * 12) & (SSI_countable > 0) & (unearned_income >= 20 * 12), SSI_countable - 0.5*(earned_income - 65 * 12), SSI_countable)

	return SSI_countable

def SSI_plot(CPS):
    count_income = CPS['unearned_income'][(CPS['SSI_target_pool']==1) & (CPS['earned_income'] >= 0)]
    SSI = CPS['ssi_val'][(CPS['SSI_target_pool']==1) & (CPS['earned_income'] >= 0)]
    fig, ax  = plt.subplots()
    plt.scatter(count_income, SSI, label = None)
    legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI for Unearned Income')
    plt.xlabel('Unearned Income')
    plt.ylabel('SSI Amount')
    # plt.ylim(0,7000)
    plt.title('Supplemental Security Income for Unearned Income Amounts')
    plt.show()

def All_SM_SSI_reg(CPS, plot = False, MTR_Calc = False):
	if MTR_Calc == False:
		gest_list = ['gestfips: '+ str(i) for i in xrange(50)]
		remove_list = ['gestfips: 28' , 'gestfips: 45', 'gestfips: 22', 'gestfips: 8', 'gestfips: 9', 
			'gestfips: 18', 'gestfips: 20', 'gestfips: 21','gestfips: 24', 'gestfips: 34', 'gestfips: 15'
			, 'gestfips: 1', 'gestfips: 42', 'gestfips: 40', 'gestfips: 23', 'gestfips: 43', 'gestfips: 31']
		gest_list = list(set(gest_list) - set(remove_list))
		string_list = ["const", "earned_income", "unearned_income"]
		together_list = string_list + gest_list
		CPS['const'] = 1.
		CPSb4 = CPS[(CPS['SSI_target_pool']==1)].copy()
		CPS = CPS[(CPS['SSI_target_pool']==1)].sample(frac=0.8, random_state=1)
		X = CPS[together_list][(CPS['SSI_target_pool']==1)]
		test = CPSb4.loc[~CPSb4.index.isin(X.index)]
		SSI = CPS['ssi_val'][(CPS['SSI_target_pool']==1)]
		model = sm.OLS(SSI, X)
		results = model.fit()
		params = results.params
		if plot == True:
			x = np.linspace(0,15000,15000)
			y = 0
			for i in xrange(len(params)):
				y += test[together_list[i]] * params[i]
			# Cross Validation:
			print 'R^2 = ', 1 - np.sum((test['ssi_val'].as_matrix()-y)**2)/np.sum((test['ssi_val'].as_matrix()-np.mean(test['ssi_val'].as_matrix()))**2)
			print 'Norm of the difference between the predicted SSI and actual SSI for all respondents: '\
				,(np.linalg.norm(test['marsupwt'].as_matrix()*(pd.Series(y).as_matrix()-test['ssi_val'].as_matrix())))/(test['marsupwt'].as_matrix().sum())
			fig, ax  = plt.subplots()
			plt.scatter( y , test['ssi_val'], label = 'SSI vs. predicted SSI')
			plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
			legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
			plt.xlabel('Predicted SSI')
			plt.ylabel('Actual SSI Amount')
			# plt.ylim(0,7000)
			plt.title('Accuracy of Linear Regresssion When Predicting SSI')
			plt.show()
	else:
		gest_list = ['gestfips: '+ str(i) for i in xrange(50)]
		remove_list = ['gestfips: 28' , 'gestfips: 45', 'gestfips: 22', 'gestfips: 8', 'gestfips: 9', 
			'gestfips: 18', 'gestfips: 20', 'gestfips: 21','gestfips: 24', 'gestfips: 34', 'gestfips: 15'
			, 'gestfips: 1', 'gestfips: 42', 'gestfips: 40', 'gestfips: 23', 'gestfips: 43', 'gestfips: 31']
		gest_list = list(set(gest_list) - set(remove_list))
		string_list = ["const", "earned_income", "unearned_income"]
		together_list = string_list + gest_list
		CPS['const'] = 1.
		X = CPS[together_list][(CPS['current_recipient']==1)]
		SSI = CPS['ssi_val'][(CPS['current_recipient']==1)]
		model = sm.OLS(SSI, X)
		results = model.fit()
		params = results.params
		x = np.linspace(0,15000,15000)
		y = params[0]
		for i in xrange(len(params)-1):
			y += CPS[together_list[i]] * params[i+1]
		# Cross Validation:
		# print 'R^2 = ', 1 - np.sum((CPS['ssi_val'].as_matrix()-y)**2)/np.sum((CPS['ssi_val'].as_matrix()-np.mean(CPS['ssi_val'].as_matrix()))**2)
		# print 'Norm of the difference between the predicted SSI and actual SSI for all respondents: '\
		# 	,(np.linalg.norm(CPS['marsupwt'].as_matrix()*(pd.Series(y).as_matrix()-CPS['ssi_val'].as_matrix())))/(CPS['marsupwt'].as_matrix().sum())
		fig, ax  = plt.subplots()
		plt.scatter( CPS['earned_income'] , CPS['ssi_val'])
		plt.plot(CPS['earned_income'].as_matrix().flatten(), y.as_matrix().flatten(), label = 'reg ssi_val on earned income', c = 'black', linewidth = 5)
		legend = ax.legend(loc = "upper right", shadow = True, title = 'Regresssion of ssi_val on earned_income')
		plt.xlabel('earned_income')
		plt.ylabel('ssi_val')
		# plt.ylim(0,7000)
		plt.title('Regresssion of ssi_val on earned_income')
		# plt.show()

	return params['earned_income'], params['const']

def RandomForest(CPS, SSI_use, plot = False, sanity_check = False, MTR_Calc = True, adjustment = 10):
    gest_list = ['gestfips']
    # gest_list = ['gestfips: '+ str(i) for i in xrange(51)]
    string_list = ["Countable_Income", "earned_income", "unearned_income"]
    predictor_columns = string_list + gest_list
    rf = RandomForestRegressor(n_estimators=100 ,max_features = 'sqrt', min_samples_leaf=15, oob_score = True)
    if MTR_Calc == False:
        train = CPS[(CPS['SSI_target_pool']==1)].sample(frac=0.8, random_state=1)
        test = CPS.loc[~CPS.index.isin(train.index)][(CPS['SSI_target_pool']==1)]    
        rf.fit(train[predictor_columns], train['calc_SSI'])
        print rf.feature_importances_
        print 'here is out-of-bag score: ' , rf.oob_score_
        if sanity_check:
            # Accuracy Diagnosis
            predictions = rf.predict(train[predictor_columns])
            print 'R^2 for %80 of training data = ', 1 - np.sum((train['ssi_val'].as_matrix()-predictions)**2)/np.sum((train['ssi_val'].as_matrix()-np.mean(train['ssi_val'].as_matrix()))**2)
            print (np.linalg.norm(train['marsupwt'].as_matrix()*(pd.Series(predictions).as_matrix()-train['ssi_val'].as_matrix())))/(train['marsupwt'].as_matrix().sum())
            if plot == True:
                x = np.linspace(np.min(predictions),np.max(predictions),15000)
                fig, ax  = plt.subplots()
                plt.scatter(predictions, train['ssi_val'], label = 'data')
                plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.xlabel('Predicted SSI')
                plt.ylabel('SSI Actual')
                # plt.ylim(0,7000)
                plt.title('Accuracy of SSI Predicted Using Random Forests (using %80 train set sanity check)')
                plt.show()
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI for unearned_income')
                plt.xlabel('Unearned Income')
                plt.ylabel('SSI Amount')
                plt.xlim(-1000,58000)
                plt.title('Predicted SSI Amounts Using Random Forests Sanity Check')
                plt.scatter(train['unearned_income'], predictions)
                plt.show()

        else:
            # Accuracy Diagnosis
            predictions = rf.predict(test[predictor_columns])
            print 'score:', rf.score(test[predictor_columns], test['calc_SSI'], test['marsupwt'])
            print 'R^2 for %20 = ', 1 - np.sum((test['calc_SSI'].as_matrix()-predictions)**2)/np.sum((test['calc_SSI'].as_matrix()-np.mean(test['calc_SSI'].as_matrix()))**2)
            print (np.linalg.norm(test['marsupwt'].as_matrix()*(pd.Series(predictions).as_matrix()-test['calc_SSI'].as_matrix())))/(test['marsupwt'].as_matrix().sum())
            if plot == True:
                x = np.linspace(np.min(predictions),np.max(predictions),15000)
                fig, ax  = plt.subplots()
                plt.scatter(predictions, test['calc_SSI'], label = 'data')
                plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.xlabel('Predicted SSI')
                plt.ylabel('SSI Actual')
                plt.title('Accuracy of SSI Predicted Using Random Forests (using %20 test set)')
                plt.show()
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI for earned_income')
                fig, ax  = plt.subplots()
                plt.xlabel('Unearned Income')
                plt.ylabel('SSI Amount')
                plt.xlim(-1000,58000)
                plt.title('Predicted SSI Amounts Using Random Forests on test set')
                plt.scatter(test['unearned_income'], predictions, c = 'black', label = 'predicted')
                plt.scatter(test['unearned_income'], test['calc_SSI'], c = 'blue', label = 'Actual')
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.show()
        return predictions
    else:
        rf.fit(CPS[predictor_columns][(CPS['SSI_target_pool']==1)], SSI_use[(CPS['SSI_target_pool']==1)])
        print 'here is out-of-bag score: ' , rf.oob_score_
        predict_SSI = rf.predict(CPS[predictor_columns][(CPS['SSI_target_pool']==1)])
        CPS['earned_income'][(CPS['SSI_target_pool']==1)] += adjustment
        ind = CPS[(CPS['SSI_target_pool']==1)].index.values
        NewSSI = rf.predict(CPS[predictor_columns][(CPS['SSI_target_pool']==1)])
        CPS['earned_income'][(CPS['SSI_target_pool']==1)] -= adjustment
        # plt.xlabel('Earned Income')
        # plt.ylabel('New SSI Amount')
        # plt.xlim(-1000,58000)
        # plt.ylim(np.min(NewSSI), np.max(NewSSI))
        # plt.title('Predicted SSI Amounts Using Random Forests on test set')
        # plt.scatter(CPS['earned_income'][(CPS['SSI_target_pool']==1)], NewSSI, c = 'black')
        # plt.show()
        MTR = (NewSSI -predict_SSI)/adjustment
        CPS['MTR_RF'] = pd.Series(np.zeros(len(CPS['earned_income'])))
        CPS.loc[ind, 'MTR_RF'] = MTR
        return MTR

def KFold_RF(CPS, plot = True):
	predictor_columns = [ "current_recipient", "earned_income", "unearned_income", "gestfips", "ssikidyn"]
	rf = RandomForestRegressor(n_estimators=100 ,max_features = 'sqrt', min_samples_leaf=3, oob_score = True)
	# knn = KNeighborsClassifier(n_neighbors=5)
	X = CPS[predictor_columns ]
	Y = CPS['ssi_val']
	scores = cross_val_score(rf, X, Y, cv=10, scoring='accuracy')
	print scores.mean()

def svr(CPS, plot = False, sanity_check = False, MTR_Calc = True ):
    # gest_list = ['gestfips']
    gest_list = ['gestfips: '+ str(i) for i in xrange(51)]
    string_list = ["earned_income", "unearned_income"]
    predictor_columns = string_list + gest_list
    svr_rbf = SVR(kernel='rbf', C=1e3, gamma=0.1)
    if MTR_Calc == False:
        train = CPS[(CPS['SSI_target_pool']==1)].sample(frac=0.8, random_state=1)
        test = CPS.loc[~CPS.index.isin(train.index)][(CPS['SSI_target_pool']==1)] 
        y_rbf = svr_rbf.fit(train[predictor_columns], train['ssi_val'])
        if sanity_check:
            # Accuracy Diagnosis
            predictions = y_rbf.predict(train[predictor_columns])
            print 'R^2 for %80 of training data = ', 1 - np.sum((train['ssi_val'].as_matrix()-predictions)**2)/np.sum((train['ssi_val'].as_matrix()-np.mean(train['ssi_val'].as_matrix()))**2)
            print (np.linalg.norm(train['marsupwt'].as_matrix()*(pd.Series(predictions).as_matrix()-train['ssi_val'].as_matrix())))/(train['marsupwt'].as_matrix().sum())
            if plot == True:
                x = np.linspace(np.min(predictions),np.max(predictions),15000)
                fig, ax  = plt.subplots()
                plt.scatter(predictions, train['ssi_val'], label = 'data')
                plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.xlabel('Predicted SSI')
                plt.ylabel('SSI Actual')
                # plt.ylim(0,7000)
                plt.title('Accuracy of SSI Predicted Using Support Vector Regressions (using %80 train set sanity check)')
                plt.show()
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI for unearned_income')
                plt.xlabel('Unearned Income')
                plt.ylabel('SSI Amount')
                plt.xlim(-1000,58000)
                plt.title('Predicted SSI Amounts Using  Support Vector Regressions Sanity Check')
                plt.scatter(train['unearned_income'], predictions)
                plt.show()

        else:
            # Accuracy Diagnosis
            predictions = y_rbf.predict(test[predictor_columns])
            print 'R^2 for %20 = ', 1 - np.sum((test['ssi_val'].as_matrix()-predictions)**2)/np.sum((test['ssi_val'].as_matrix()-np.mean(test['ssi_val'].as_matrix()))**2)
            print (np.linalg.norm(test['marsupwt'].as_matrix()*(pd.Series(predictions).as_matrix()-test['ssi_val'].as_matrix())))/(test['marsupwt'].as_matrix().sum())
            if plot == True:
                x = np.linspace(np.min(predictions),np.max(predictions),15000)
                fig, ax  = plt.subplots()
                plt.scatter(predictions, test['ssi_val'], label = 'data')
                plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.xlabel('Predicted SSI')
                plt.ylabel('SSI Actual')
                # plt.ylim(0,7000)
                plt.title('Accuracy of SSI Predicted Using Support Vector Regressions (using %20 test set)')
                plt.show()
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI for earned_income')
                fig, ax  = plt.subplots()
                plt.xlabel('Unearned Income')
                plt.ylabel('SSI Amount')
                plt.xlim(-1000,58000)
                plt.title('Predicted SSI Amounts Using  Support Vector Regressions on test set')
                plt.scatter(test['unearned_income'], predictions, c = 'black', label = 'predicted')
                plt.scatter(test['unearned_income'], test['ssi_val'], c = 'blue', label = 'Actual')
                legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
                plt.show()
        return predictions
    else:
        y_rbf.fit(CPS[predictor_columns][(CPS['SSI_target_pool']==1)], CPS["ssi_val"][(CPS['SSI_target_pool']==1)])
        CPS['earned_income'][(CPS['SSI_target_pool']==1)] += 1
        NewSSI = y_rbf.predict(CPS[predictor_columns][(CPS['SSI_target_pool']==1)])
        CPS['earned_income'] -= 1
        plt.xlabel('Earned Income')
        plt.ylabel('New SSI Amount')
        plt.xlim(-1000,58000)
        plt.ylim(np.min(NewSSI), np.max(NewSSI))
        plt.title('Predicted SSI Amounts Using Random Forests on test set')
        plt.scatter(CPS['earned_income'][(CPS['SSI_target_pool']==1)], NewSSI, c = 'black')
        plt.show()
        MTR = (NewSSI - CPS['ssi_val'][(CPS['SSI_target_pool']==1)])
        return MTR

def Neural(CPS, plot = False):
	train = CPS[(CPS['SSI_target_pool']==1)].sample(frac=0.8, random_state=1)
	test = CPS.loc[~CPS.index.isin(train.index)][(CPS['SSI_target_pool']==1)]
	gest_list = ['gestfips: '+ str(i) for i in xrange(51)]
	string_list = ["earned_income", "unearned_income", "ssi_val"]
	predictor_columns = gest_list + string_list
	CPS = train[predictor_columns]
	mean = CPS.mean()['ssi_val']
	maxi = CPS.max()['ssi_val']
	mini = CPS.min()['ssi_val']
	Series = CPS[string_list].copy().apply(lambda x: (x - np.mean(x)) / (np.max(x) - np.min(x)))
	CPS[string_list] = Series
	N_inp = len(predictor_columns)-1
	N_out = 1 
	ds = pb.datasets.SupervisedDataSet(N_inp, N_out) 
	for sample in CPS[predictor_columns].values: 
		ds.addSample(sample[:N_inp], sample[N_inp:]) 
	n = buildNetwork(ds.indim,ds.indim-2, ds.indim, ds.outdim,recurrent=True)
	t = BackpropTrainer(n, ds, learningrate=0.01,momentum=0.5,verbose=True)
	t.trainUntilConvergence(dataset=ds, maxEpochs=40, verbose=None, continueEpochs=10, validationProportion=0.25)
	predictions = (n.activateOnDataset(ds)).flatten()
	predictions = (predictions * (maxi - mini)) + mean
	CPS[string_list] = CPS[string_list].apply(lambda x: x * (maxi - mini) + mean)
	# print predictions.shape
	print 'R^2 = ', 1 - np.sum((CPS['ssi_val'].as_matrix()-predictions)**2)/np.sum((CPS['ssi_val'].as_matrix()-np.mean(CPS['ssi_val'].as_matrix()))**2)

	if plot == True:
		x = np.linspace(np.min(predictions),np.max(predictions),15000)
		fig, ax  = plt.subplots()
		plt.scatter(predictions, CPS['ssi_val'], label = 'data')
		plt.plot(x, x, label = 'perfect fit', c = 'black', linewidth = 5)
		legend = ax.legend(loc = "upper right", shadow = True, title = 'SSI against SSI predicted')
		plt.xlabel('Predicted SSI')
		plt.ylabel('SSI Actual')
		# plt.ylim(0,7000)
		plt.title('Accuracy of SSI Predicted Using Random Forests (using %20 test set)')
		plt.show()
	return predictions

# '''loading in data'''

# '''three years of CPS combined'''
# CPS = pd.read_csv('CPS_SSI_Combined.csv')
# '''March 2014 CPS only'''
CPS = pd.read_csv('CPS_SSI.csv')
# '''Creates dummy variables for all 50 states'''
CPS_dummy_states = dmatrix('C(gestfips)- 1', CPS, return_type='dataframe')

i = 0
for name in CPS_dummy_states.columns.values:
	CPS_dummy_states.rename(columns={name : str('gestfips: '+ str(i))}, inplace=True)
	i+=1
CPS = pd.concat([CPS, CPS_dummy_states], axis = 1)

# '''dropping insignificant states'''
CPS.drop(['gestfips: 28' , 'gestfips: 45', 'gestfips: 22', 'gestfips: 8', 'gestfips: 9', 'gestfips: 18', 
	'gestfips: 20', 'gestfips: 21','gestfips: 24', 'gestfips: 34', 
	'gestfips: 15', 'gestfips: 1', 'gestfips: 42', 'gestfips: 40', 'gestfips: 23', 'gestfips: 43', 'gestfips: 31'], axis=1, inplace=True)

CPS['deemed_income_y'] = CPS['deemed_income_y'].fillna(0)
CPS.drop('eligible_spouse_x', axis=1, inplace=True)
CPS['eligible_spouse_y'] = CPS['eligible_spouse_y'].fillna(0)

#'''deemed_income_y is the deemed income of the spouse assigned to respondent '''

SSI = np.zeros(len(CPS['earned_income']))
ind = CPS.loc[CPS['current_recipient'] ==1, 'current_recipient'].index.values
CPS['Countable_Income'] = countable(CPS['earned_income'], CPS['unearned_income'])
for i in ind:
	SSI[i] = Fed_SSI(CPS.loc[i, 'a_spouse'], CPS.loc[i ,'Countable_Income'], CPS.loc[i, 'deemed_income_y'])

# Average distance between calculated SSI and CPS SSI values using everyone:
# print np.linalg.norm(SSI - CPS['ssi_val'])/ len(SSI)

# Average distance between calculated SSI and CPS SSI values using only current SSI recipients:
# print np.linalg.norm(SSI[CPS[CPS['current_recipient'] == 1].index.values] - CPS['ssi_val'][CPS['current_recipient'] == 1])/ len(CPS['ssi_val'][CPS['current_recipient'] == 1])

# print np.max(SSI), np.min(SSI), np.max(CPS['ssi_val']), np.min(CPS['ssi_val'])

'''SSI calculated from income rules'''

CPS['calc_SSI'] = SSI
CPS['earned_income'] += 1
CPS['Countable_Income'] = countable(CPS['earned_income'], CPS['unearned_income'])


SSI_after = np.zeros(len(CPS['earned_income']))

'''calculated SSI after earned income adjustment'''
for i in ind:
	SSI_after[i] = Fed_SSI(CPS.loc[i, 'a_spouse'], CPS.loc[i ,'Countable_Income'], CPS.loc[i, 'deemed_income_y'])

MTR_Program = SSI_after - SSI

CPS['earned_income'] -= 1

ineligible_spouses = CPS.loc[CPS[(CPS['eligible_spouse_y'] ==1) & (CPS['current_recipient'] == 0)].index.values, 'current_recipient'].index.values
# MTR_Program[ineligible_spouses] = -0.25
# eligible_w_eligible_spouses = CPS.loc[CPS[(CPS['eligible_spouse_y'] ==1) & (CPS['current_recipient'] == 1)].index.values, 'current_recipient'].index.values

CPS['a_spouse_bin'] = np.where(CPS['a_spouse'] != 'None or children', 1, 0)
MTR_RF = RandomForest(CPS, CPS["ssi_val"],  plot = False, sanity_check = False, MTR_Calc = True, adjustment = 10)
# MTR_RF = RandomForest(CPS, CPS["calc_SSI"], plot = False, sanity_check = False, MTR_Calc = True, adjustment = 1)

income_cutoffs_list = []
for i in xrange(50):
	income_cutoffs_list.append(CPS['earned_income'][CPS['current_recipient']==1].quantile((i+1) * .02))

#top 90% earners among SSI receivers:
income_cutoffs_list = income_cutoffs_list[44:]
CPS['MTR_computed'] = pd.Series(MTR_Program)
Program_MTR_zero = []
Program_MTR_positive = []
Program_MTR = [Program_MTR_zero, Program_MTR_positive]
# SSI_plot(CPS)

'''add iterations with different earned income values later'''

CPS = CPS[CPS['current_recipient'] == 1]
df_zero = CPS[(CPS['earned_income'] == 0)]
print np.unique(df_zero['MTR_computed'])
slope, intercept = All_SM_SSI_reg(df_zero, plot = False, MTR_Calc = True)
Program_MTR[0].append(['income =' + str(0), \
    (np.sum(df_zero['marsupwt'] * df_zero['MTR_computed'])/(np.sum(df_zero['marsupwt']))), (np.sum(df_zero['marsupwt'] * 
    	df_zero['MTR_RF'])/(np.sum(df_zero['marsupwt']))), slope])


df_single = CPS[(CPS['earned_income'] > 0) & (CPS['a_spouse'] == 'None or children')]
print np.unique(df_single['MTR_computed'])
slope, intercept = All_SM_SSI_reg(df_single, plot = False, MTR_Calc = True)
Program_MTR[1].append(['single and income >' + str(0), \
    (np.sum(df_single['marsupwt'] * df_single['MTR_computed'])/(np.sum(df_single['marsupwt']))), (np.sum(df_single['marsupwt'] * 
    	df_single['MTR_RF'])/(np.sum(df_single['marsupwt']))), slope])

df_married = CPS[(CPS['earned_income'] > 0) & (CPS['a_spouse'] != 'None or children')]
print np.unique(df_married['MTR_computed'])
slope, intercept = All_SM_SSI_reg(df_married, plot = False, MTR_Calc = True)
Program_MTR[1].append(['married and income >' + str(0), \
    (np.sum(df_married['marsupwt'] * df_married['MTR_computed'])/(np.sum(df_married['marsupwt']))), (np.sum(df_married['marsupwt'] * 
    	df_married['MTR_RF'])/(np.sum(df_married['marsupwt']))), slope])

print tabulate.tabulate([item for sublist in Program_MTR for item in sublist], tablefmt = "latex")

