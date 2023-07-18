from flask import Flask, render_template
import plotly.graph_objs as go

app = Flask(__name__)

@app.route('/')
def index():
    # Sample data for the bar chart
    x_values = ['A', 'B', 'C', 'D']
    y_values = [10, 25, 5, 15]

    # Create a Plotly bar chart
    bar_chart = go.Figure(data=[go.Bar(x=x_values, y=y_values)])

    # Convert the chart to JSON to pass to the template
    graphJSON = bar_chart.to_json()

    # Render the template with the graph data
    return render_template('index.html', graphJSON=graphJSON)

if __name__ == '__main__':
    app.run(debug=True)
