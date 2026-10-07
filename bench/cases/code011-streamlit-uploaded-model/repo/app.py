import pickle

import pandas as pd
import streamlit as st

st.title("Try your model")
uploaded = st.file_uploader("Model (.pkl)", type=["pkl"])
data = st.file_uploader("Data (.csv)", type=["csv"])

if uploaded and data:
    model = pickle.load(uploaded)
    df = pd.read_csv(data)
    st.write(model.predict(df))
