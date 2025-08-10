***Changes Made***

1.) Removed Stop-words from the dataset to improve model accuracy of the model 

2.) tweaked  the parameters of random forest classifier to achieve the best hyperparameter tuning setup for the model 

3.) Added reasons and definitions at certain places to improve readability and understandability. 

4.) Visualised the model performance metrics using barplot and confusion matrix to better understand the performance of the model. \


***Model Performance*** 

**Before removing stop-words**

-> accuracy score is: 0.72856 

-> precision score is: 0.7363782051282052 

-> recall score is: 0.7244206211571812 

-> f1 score is: 0.7303504728602083 



**After removing stop words**

-> accuracy score is: 0.75816
 
-> precision score is: 0.7614996849401386

-> recall score is: 0.762099952703768

-> f1 score is: 0.7617997005752107 


 


**After Changing Random Forest parameters** 

-> Stop words removed.

( n_estimators=20 
criterion = "entropy" ) 

-> accuracy score is: 0.81736
 
-> precision score is: 0.8382205931356215

-> recall score is: 0.7931578117609964

-> f1 score is: 0.8150668286755771

( n_estimators=100
criterion = "entropy" ) 

-> accuracy score is: 0.8628
 
-> precision score is: 0.867185020628372

-> recall score is: 0.8615796941510326

-> f1 score is: 0.8643732700672202 

( n_estimators=100
criterion = "gini" )  

-> accuracy score is: 0.858

-> precision score is: 0.8696989316931045
 
-> recall score is: 0.8470755163172

-> f1 score is:  0.8582381598913825
