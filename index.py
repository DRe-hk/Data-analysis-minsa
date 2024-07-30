import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import json

app = Dash(__name__)


# Diccionario de enfermedades y sus archivos CSV
enfermedades = {
    "Hipertension": "Dataset_Hipertension_Puno.csv",
    "Enfermedad Renal": "Dateset_EnfermedadRenal_Puno.csv",
    "Diabetes": "Dataset_Diabetes_Puno.csv",
    "Obesidad": "Dataset_Obesidad_Puno.csv",
    "Hiperlipidemia": "Dataset_Hiperlipidemia_Puno.csv"
    # Añade más enfermedades y sus archivos correspondientes aquí
}

# Leer el archivo geojson
with open('peru_distrital_simple.geojson', 'r', encoding='utf-8') as f:
    geojson_file = json.load(f)

def get_year_from_date(date_str):
    return date_str[:4] if isinstance(date_str, str) else None

# Layout de la aplicación
app.layout = html.Div(className='container', children=[
    html.Div(className='header', children=[
        html.H1("Análisis de Enfermedades", className='title'),
    ]),
    html.Div(className='content', children=[
        html.Div(className='map_container', children=[
            dcc.Graph(id='map_graph', style={'height': '100%'})
        ]),
        html.Div(className='sidebar', children=[
            dcc.Dropdown(
                id="slct_enfermedad",
                options=[{"label": enfermedad, "value": archivo} for enfermedad, archivo in enfermedades.items()],
                value=list(enfermedades.values())[0],
                className='dbc'
            ),
            html.Div(id='summary', className='summary'),
            
            dcc.Dropdown(
                id="slct_metric_1",
                options=[
                    {"label": "Ambos", "value": "AMBOS"},
                    {"label": "Femenino", "value": "FEMENINO"},
                    {"label": "Masculino", "value": "MASCULINO"},
                ],
                multi=False,
                value="AMBOS",
                className='dbc'
            ),
            dcc.Dropdown(
                id="slct_metric_2",
                options=[{"label": f"{i}-{i+9}", "value": f"{i}-{i+9}"} for i in range(0, 100, 10)] + [{"label": "Todas las edades", "value": "TODAS"}],
                multi=False,
                value="TODAS",
                className='dbc'
            ),
            dcc.Dropdown(
                id="slct_metric_3",
                options=[],
                multi=False,
                value="TODOS",
                className='dbc'
            ),
            dcc.Dropdown(
                id="slct_metric_4",
                options=[],
                multi=False,
                value="TODOS",
                className='dbc'
            ),

            dcc.Graph(id='bar_graph', className='graph')
        ])
    ])
])

# Populate year and province dropdown options dynamically based on the dataset
@app.callback(
    [Output(component_id='slct_metric_3', component_property='options'),
     Output(component_id='slct_metric_4', component_property='options')],
    [Input(component_id='slct_enfermedad', component_property='value')]
)

def update_dropdown_options(selected_enfermedad):
    df = pd.read_csv(selected_enfermedad, delimiter=',', encoding='utf-8')
    
    # Generate year options
    df['YEAR'] = df['FECHA_MUESTRA'].astype(str).apply(get_year_from_date)
    year_options = [{"label": str(year), "value": str(year)} for year in sorted(df['YEAR'].unique())]
    year_options.insert(0, {"label": "Todos los años", "value": "TODOS"})
    
    # Generate province options
    province_options = [{"label": province, "value": province} for province in sorted(df['PROVINCIA'].unique())]
    province_options.insert(0, {"label": "Toda la región", "value": "TODOS"})
    
    return year_options, province_options

# Generate dataframes based on selected filters
def filter_dataframe(df, gender, age_range, year, province):
    if gender != "AMBOS":
        df = df[df['SEXO_PACIENTE'] == gender]
    if age_range != "TODAS":
        age_min, age_max = map(int, age_range.split('-'))
        df = df[(df['EDAD_PACIENTE'] >= age_min) & (df['EDAD_PACIENTE'] <= age_max)]
    if year != "TODOS":
        df['YEAR'] = df['FECHA_MUESTRA'].astype(str).apply(get_year_from_date)
        df = df[df['YEAR'] == year]
    if province != "TODOS":
        df = df[df['PROVINCIA'] == province]
    return df

# Callback para actualizar el mapa y el gráfico de barras
@app.callback(
    [Output(component_id='map_graph', component_property='figure'),
    Output(component_id='bar_graph', component_property='figure'),
     Output(component_id='summary', component_property='children')],
    [Input(component_id='slct_enfermedad', component_property='value'),
     Input(component_id='slct_metric_1', component_property='value'),
     Input(component_id='slct_metric_2', component_property='value'),
     Input(component_id='slct_metric_3', component_property='value'),
     Input(component_id='slct_metric_4', component_property='value')]
)
def update_graph(selected_enfermedad, selected_gender, selected_age_range, selected_year, selected_province):
    # Cargar el dataset correspondiente

    df1 = pd.read_csv(selected_enfermedad, delimiter=',', encoding='utf-8')
    total_casos = len(df1)
    distritos_afectados = df1['DISTRITO'].nunique()
    edad_promedio = df1['EDAD_PACIENTE'].mean() if 'EDAD_PACIENTE' in df1.columns else 'No disponible'
    genero_mas_comun = df1['SEXO_PACIENTE'].mode()[0] if 'SEXO_PACIENTE' in df1.columns else 'No disponible'

    df = filter_dataframe(df1, selected_gender, selected_age_range, selected_year, selected_province)
    df_map = df.groupby('DISTRITO').size().to_frame(name='Cantidad')
    df_map.reset_index(inplace=True)


    color_scale = [
        [0, "#f2fffb"],      # 0
        [0.14, "#bbffeb"],   # 500
        [0.28, "#98ffe0"],   # 1000
        [0.43, "#79ffd6"],   # 1500
        [0.57, "#6df0c8"],   # 2000
        [0.71, "#59dab2"],   # 2500
        [0.86, "#31c194"],   # 3000
        [1, "#10523e"]       # 3500
    ]


    # Mapa
    map_fig = px.choropleth_mapbox(
        data_frame=df_map,
        geojson=geojson_file,
        locations='DISTRITO',
        featureidkey="properties.NOMBDIST",
        color='Cantidad',
        range_color=(0, df_map['Cantidad'].max()),
        mapbox_style="carto-darkmatter",
        zoom=7,
        center={"lat": -14.99758125369731, "lon": -70.0228036805993},
        opacity=1,
        hover_data=['DISTRITO', 'Cantidad'],
        color_continuous_scale=color_scale,
        template='plotly_dark'
    )

    summary = html.Div([
            html.P(f"Total de casos: {total_casos}"),
            html.P(f"Distritos afectados: {distritos_afectados}"),
            html.P(f"Edad promedio: {edad_promedio:.2f}" if isinstance(edad_promedio, float) else f"Edad promedio: {edad_promedio}"),
            html.P(f"Género más común: {genero_mas_comun}")
    ])
    
    bar_fig = px.histogram(
        df, 
        x='EDAD_PACIENTE', 
        color='SEXO_PACIENTE', 
        barmode='group', 
        template='plotly_dark',
        title="Distribución por Edad y Sexo",
        labels={'EDAD_PACIENTE': 'Edad', 'SEXO_PACIENTE': 'Sexo'},
        color_discrete_sequence=["#10523e" ,'#bbffeb' ]
    )

    return map_fig, bar_fig, summary

if __name__ == '__main__':
    app.run_server(debug=True)
