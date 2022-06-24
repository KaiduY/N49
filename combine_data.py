"""This small script glues together the data generated during the experiment into one single file."""
import pandas as pd

path0 = './n49/output0.csv'
path1 = './n49/output1.csv'

d0 = pd.read_csv(path0)
d1 = pd.read_csv(path1)

dall = pd.concat([d0, d1], ignore_index=True)

dall.to_csv('data.csv', index=False)

