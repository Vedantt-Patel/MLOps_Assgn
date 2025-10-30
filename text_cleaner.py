from sklearn.base import BaseEstimator, TransformerMixin
import re
import string

class TextCleaner(BaseEstimator, TransformerMixin):
    def clean_text(self, text):
        text = str(text).lower()
        text = re.sub(r'https?://\S+|www\.\S+', '', text) 
        text = re.sub(r'\d+', '', text)  
        text = text.translate(str.maketrans('', '', string.punctuation)) 
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.apply(self.clean_text)