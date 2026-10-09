import pickle
import streamlit as st

st.title("Model explorer")
model = pickle.load(st.file_uploader("Model (.pkl)"))
st.write(type(model).__name__)
