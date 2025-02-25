from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus.flowables import HRFlowable
import os
import pandas as pd

# a list to hold the dataframes from each file
dfs = []

for f in os.listdir(os.getcwd()):
    if f.startswith('r_statista'):
        df = pd.read_csv(f)

        # populate the study country and year columns from the filename
        df[['study','country','year']] = [f.split('_')[t] for t in [2,3,4]]

        # remove the .csv suffix and populate a filename column
        df['year'] = df.year.str.replace('.csv', '', regex=True).astype(int)
        df['filename'] = f

        dfs.append(df)

# combine the list of dfs into a single df
df_result = pd.concat(dfs)

# produce a summary to inspect what we have
grouped = df_result.groupby(['country','year','study','filename'])['rank'].count()


# Create PDF report
doc = SimpleDocTemplate("report.pdf", pagesize=letter)
elements = []

# Define title paragraph style
title_style = ParagraphStyle(
    name='TitleStyle',
    fontName='Helvetica-Bold',
    fontSize=24,
    textColor=colors.black,
    leftIndent=10,
    spaceBefore=10,
    spaceAfter=5,
)

# Create title paragraph
title = Paragraph("Available Files", title_style)

# Add title to elements
elements.append(title)

# Add solid line under title
line = HRFlowable(width="100%", thickness=1, lineCap='round', color="black", spaceBefore=20, spaceAfter=5)
elements.append(line)

# Add space after the line
elements.append(Spacer(1, 10 * mm))
# Convert groupby object to Pandas DataFrame
grouped_df = grouped.reset_index()

# Determine column types
column_types = grouped_df.dtypes.to_dict()
header_row = grouped_df.columns.values.tolist()
table_data = [header_row] + grouped_df.values.tolist()
# table_data = table_data.values.tolist()

# Create table from DataFrame
table = Table(table_data)

# Set table style
table_style = [('BACKGROUND', (0, 0), (-1, 0), colors.bisque),
               ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
               ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
               ('FONTNAME', (0, 0), (-1, 0), 'Courier'),
               ('FONTSIZE', (0, 0), (-1, 0), 14),
               ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
               ('BACKGROUND', (0, 1), (-1, -1), (1, 1, 1)),
               ('GRID', (0, 0), (-1, -1), 1, (0.90, 0.90, 0.90))]

# Determine column types
column_types = grouped_df.dtypes.to_dict()

# Set alignment for each column based on column type
for i, column in enumerate(grouped_df.columns):
    if column_types[column] == 'object':
        table_style += [('ALIGN', (i, 1), (i, -1), 'LEFT')]
    elif column_types[column] == 'int64' or column_types[column] == 'float64':
        table_style += [('ALIGN', (i, 1), (i, -1), 'RIGHT')]

table.setStyle(TableStyle(table_style))

# Add table to document
elements.append(table)

# Build PDF report
doc.build(elements)

os.startfile('report.pdf')