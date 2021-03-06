##Imports
print("Importing necessary libraries")
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import random
from scipy.stats import zscore
import itertools


##Sklearn Imports
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.decomposition import PCA
from sklearn.metrics import auc, roc_curve
from sklearn import svm
from sklearn.model_selection import train_test_split as TTS
from sklearn.preprocessing import label_binarize
from sklearn.metrics import classification_report, confusion_matrix

##########################################################
##Print Message Function and Plot Confusion Matrix
##########################################################
def print_message(string):
    print('#'*(len(string) + 2))
    print('#'+string+'#')
    print('#'*(len(string) + 2))

##From sklearn
##http://scikit-learn.org/stable/auto_examples/model_selection/plot_confusion_matrix.html
def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues, fname = ""):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    plt.figure()
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.tight_layout()
    plt.savefig(fname)
##########################################################


##########################################################
##Loading, Concatenating, and Cleaning the Data for Analysis
##########################################################

##Load in data
print("\n\nLoading in the Data")
# data_df = pd.read_csv("full_data.csv")
data_df = pd.read_csv("../data.csv") ##Local Development Copy

##Extract Class Predictions and make them discrete integers
print("Transforming classes into integers for the model")
labels = data_df['Health'].values
unique_labs = np.unique(labels)
y_true = []
for i in labels:
    y_true.append([j for j in range(len(unique_labs)) if unique_labs[j] == i][0])

##Extract the indices for the tags for the bacterial/viral data
print("Getting the bacterial/viral counts from the data and clinical symptoms\n")
first_tag = 'Bacteroidetes'
last_tag = 'Virus'
first_loc = [x for x in range(len(data_df.columns)) if data_df.columns[x] == first_tag][0]
last_loc = [x+1 for x in range(len(data_df.columns)) if data_df.columns[x] == last_tag][0]

##Get the names of those features from the data
print("Getting feature names from data")
micro_bio_colums = data_df.columns[first_loc:last_loc]

##Getting the clinical columns
first_tag = 'No Symptoms'
last_tag = 'Fever'
first_loc = [x for x in range(len(data_df.columns)) if data_df.columns[x] == first_tag][0]
last_loc = [x+1 for x in range(len(data_df.columns)) if data_df.columns[x] == last_tag][0]
clinical_columns = data_df.columns[first_loc:last_loc]

##Extract the matrix of expression data and normalize
##Log2 transform and the z-score normalization
micro_bio_data = data_df[micro_bio_colums].values.astype(float)
micro_bio_data = np.log2(micro_bio_data)
micro_bio_data[np.isnan(micro_bio_data)] = -1
micro_bio_data[np.isinf(micro_bio_data)] = -1
micro_bio_data = zscore(micro_bio_data, axis = 1)
micro_bio_data[np.isnan(micro_bio_data)] = -1

try:
    clinical_data = data_df[clinical_columns].values.astype(float)
except:
    clinical_data = data_df[clinical_columns].values.astype(str)
    def subset(item):
        return item.split(" ")[0].lower()
    subset_array = np.vectorize(subset)
    clinical_data = subset_array(clinical_data)
    clinical_data[clinical_data == 'nan'] = "-1"
    clinical_data[clinical_data == 'missing'] = "-1"
    clinical_data[clinical_data == 'yes'] = "1"
    clinical_data[clinical_data == 'no'] = "0"
    clinical_data = clinical_data.astype(float)

##Total Features
features = np.array(list(clinical_columns)+list(micro_bio_colums))

##Final Model Data
X = np.concatenate((clinical_data,micro_bio_data), axis = 1)
y = y_true

print_message("Data Loaded and Ready!!")
##########################################################
##########################################################

print('\n')

##########################################################
##Random Forest Classifier
##########################################################

##Make dictionary to store model importances
print_message("Working on RFC")

model_importances = {}
for feature in list(clinical_columns)+list(micro_bio_colums):
    model_importances[feature] = 0

##Store AUC for CV
auc_validations = {}
for k in np.unique(y_true):
    auc_validations[k] = []

##K-fold Cross Validation
for T in range(20):
    ##Train-Test Split
    X_train, X_test, y_train, y_test = TTS(X, y, test_size = 0.25)

    ##Train the Model
    # print("Building RFC model\n")
    rfc = RFC(n_estimators=30, n_jobs = 5)
    rfc.fit(X_train, y_train)
    y_pred = rfc.predict_proba(X_test)
    y_pred_b = rfc.predict(X_test)

    ##Create encoding for AUC
    y_test_e = label_binarize(y_test, classes = np.unique(y_test))

    # Compute ROC Curve and AUC for each class
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    for i in range(y_test_e.shape[1]):
        fpr[i], tpr[i], _ = roc_curve(y_test_e[:, i], y_pred[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])
    for k in roc_auc.keys():
        auc_validations[k].append(roc_auc[k])


    ##Extract Feature Importances
    importances = rfc.feature_importances_
    sorted_inds = np.argsort(importances)[::-1]
    sorted_features = features[sorted_inds]
    sorted_importances = importances[sorted_inds]

    for i,val in enumerate(sorted_features):
        model_importances[val] += sorted_importances[i]

    if T==19:
        rfc = plot_confusion_matrix(confusion_matrix(y_test, y_pred_b), classes = ["Sick", "Healthy", "Follow"], fname = "../results/random_forest.png")
        print(confusion_matrix(y_test, y_pred_b))
        print(classification_report(y_test, y_pred_b))


##Print Results for Random Forest
print_message("Random Forest Classifier")
print('\n'+"After {} Trials:".format(T+1))
for k in auc_validations.keys():
    print("AUC {}: {}".format(unique_labs[k], round(np.mean(auc_validations[k]),4)))

##Final Feature Importances Plot
importances = np.array(list(model_importances.values()))
sorted_inds = np.argsort(importances)[::-1]
sorted_importances = importances[sorted_inds]/len(importances)
features = np.array(list(model_importances.keys()))
sorted_features = features[sorted_inds]
plt.figure(figsize=(13, 7))
ax = plt.gca()
ax.bar(range(len(sorted_inds)), sorted_importances)
ax.set_title("Feature Importances", fontsize = 23)
ax.set_ylabel("Feature Importances", fontsize = 16)
ax.set_xlabel("Feature", fontsize = 16)
ax.set_xticks(range(len(sorted_inds)))
ax.set_xticklabels(sorted_features, rotation = 90)
plt.tight_layout()
plt.savefig("../results/full_w_clinical_importances.png", dpi = 200, bbox_inches = 'tight')

to_save = np.array(importances)
np.savetxt("../results/importances_in_order_of_features.txt", to_save)

##########################################################

print('\n')

##########################################################
##Linear SVM
##########################################################
print_message("Working on Linear Support Vector Machine")

##Store AUC for CV
auc_validations = {}
for k in np.unique(y_true):
    auc_validations[k] = []

##Cross Validation by Repeat Trials
for T in range(20):
    # print("Trial {}".format(T+1))
    ##Train-Test Split
    X_train, X_test, y_train, y_test = TTS(X, y, test_size = 0.25)

    ##Train the Model
    classifier = OneVsRestClassifier(svm.SVC(kernel='linear', probability=True))
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict_proba(X_test)
    y_pred_b = classifier.predict(X_test)

    ##Create encoding for AUC
    y_test_e = label_binarize(y_test, classes = np.unique(y_true))

    # Compute ROC Curve and AUC for each class
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    for i in range(y_test_e.shape[1]):
        fpr[i], tpr[i], _ = roc_curve(y_test_e[:,i], y_pred[:,i])
        roc_auc[i] = auc(fpr[i], tpr[i])
    for k in roc_auc.keys():
        auc_validations[k].append(roc_auc[k])

    if T==19:
        lin_reg = plot_confusion_matrix(confusion_matrix(y_test, y_pred_b), classes = ["Sick", "Healthy", "Follow"], fname = "../results/lin_svm.png")
        print(confusion_matrix(y_test, y_pred_b))
        print(classification_report(y_test, y_pred_b))

##Print Results
print_message("Linear SVM")
print('\n'+"After {} Trials:".format(T+1))
for k in auc_validations.keys():
    print("AUC {}: {}".format(unique_labs[k], round(np.mean(auc_validations[k]),4)))

##########################################################

print('\n')

##########################################################
##Logistic Regression
##########################################################
print_message("Working on Logistic Regression")

##Store AUC for CV
auc_validations = {}
for k in np.unique(y_true):
    auc_validations[k] = []

##Cross Validation by Repeat Trials
for T in range(20):
    ##Train-Test Split
    X_train, X_test, y_train, y_test = TTS(X, y, test_size = 0.25)

    ##Train the Model
    classifier = LogisticRegression()
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict_proba(X_test)
    y_pred_b = classifier.predict(X_test)

    ##Create encoding for AUC
    y_test_e = label_binarize(y_test, classes = np.unique(y_true))

    # Compute ROC Curve and AUC for each class
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    for i in range(y_test_e.shape[1]):
        fpr[i], tpr[i], _ = roc_curve(y_test_e[:,i], y_pred[:,i])
        roc_auc[i] = auc(fpr[i], tpr[i])
    for k in roc_auc.keys():
        if roc_auc[k] != np.nan:
            auc_validations[k].append(roc_auc[k])

    if T==19:
        log_reg = plot_confusion_matrix(confusion_matrix(y_test, y_pred_b), classes = ["Sick", "Healthy", "Follow"], fname = "../results/log_reg.png")
        print(confusion_matrix(y_test, y_pred_b))
        print(classification_report(y_test, y_pred_b))

##Print Results
print_message("Logistic Regression")
print('\n'+"After {} Trials:".format(T+1))
for k in auc_validations.keys():
    print("AUC {}: {}".format(unique_labs[k], round(np.mean(auc_validations[k]),4)))

##########################################################


##########################################################
##Comaprison to Methods
##########################################################
##K to try
ks = [2,3,4,5,6,7,8,9,10]

##Run pca take first 5 principle components
X = PCA(n_components = 5).fit_transform(X)

for K in ks:

    ##Store Adjusted Rand Indices
    rand_indexes = {"Log,RFC":0, "Log,KMeans":0, "Log,Lin":0, "RFC,KMeans":0, "RFC,Lin":0, "KMeans,Lin":0}

    print_message("Comparison Results for K={}".format(K))

    ##Cross Validation by Repeat Trials
    cnt = 1
    for T in range(20):

        ##Train-Test Split
        X_train, X_test, y_train, y_test = TTS(X, y, test_size = 0.25)

        ##Logistic Regression
        lr_classifier = LogisticRegression()
        y_pred_log = lr_classifier.fit(X_train, y_train).predict(X_test)

        ##Random Forest
        rfc = RFC(n_estimators=30, n_jobs = 5)
        rfc.fit(X_train, y_train)
        y_pred_rf = rfc.predict(X_test)

        ##KMeans
        ##Assigns new data to the nearest centroid
        kmeans = KMeans(n_clusters = K)
        kmeans.fit(X_train, y_train)
        y_pred_km = kmeans.predict(X_test)

        ##Linear SVM
        classifier = OneVsRestClassifier(svm.SVC(kernel='linear', probability=True))
        y_pred_lin = classifier.fit(X_train, y_train).predict(X_test)

        rand_indexes["Log,RFC"] += adjusted_rand_score(y_pred_log, y_pred_rf)
        rand_indexes["Log,KMeans"] += adjusted_rand_score(y_pred_log, y_pred_km)
        rand_indexes["Log,Lin"] += adjusted_rand_score(y_pred_log, y_pred_lin)
        rand_indexes["RFC,KMeans"] += adjusted_rand_score(y_pred_rf, y_pred_km)
        rand_indexes["RFC,Lin"] += adjusted_rand_score(y_pred_rf, y_pred_lin)
        rand_indexes["KMeans,Lin"] += adjusted_rand_score(y_pred_km, y_pred_lin)
        cnt += 1

    ##Print Result
    print("Result for K = {}".format(K))
    for key in rand_indexes.keys():
        print("{}: {}".format(key, round(rand_indexes[key]/cnt, 4)))
    print("\n")

##########################################################
