import { Bar, Doughnut, Line, Pie, PolarArea, Radar } from "react-chartjs-2";
import Chart from 'chart.js/auto'
import React from "react";


// Accept chartRef to get the chart instance
export function getChart(data, options, selectedChart){ 
    // The 'options' object passed in already contains responsive: true and maintainAspectRatio: false
    // We just need to pass it directly to the chart components.
    // console.log({data: data, options: options, selectedChart: selectedChart})
    switch (selectedChart) {
        case "Bar":
          return <Bar data={data} options={options} />; // Pass options directly
        case "Line":
          return <Line data={data} options={options} />; // Pass options directly
        case "Radar":
          // Radar charts might need specific scale options, but responsiveness is handled by the base options
          return <Radar data={data} options={options} />; // Pass options directly
        case "Doughnut":
          return <Doughnut data={data} options={options} />; // Pass options directly
        case "Pie":
          return <Pie data={data} options={options} />; // Pass options directly
        case "PolarArea":
          return <PolarArea data={data} options={options} />; // Pass options directly
        default:
          // Default to Bar chart, passing the options directly
          return <Bar data={data} options={options} />; 
    }
}

export function showChart(data, selectedChart, message) {
    const values = data.datasets[0].data;
    const maxVal = Math.max(...values);
    const roundedMax = Math.ceil(maxVal / 50) * 55;

    const options = {
       responsive: true,
       maintainAspectRatio: false,
       scales: {
        y: {
        beginAtZero: true,
        suggestedMax: roundedMax,
        title: {
        display: true,
        text: "App Calls", // ✅ Y-axis title
        font: {
          size: 14,
          weight: "bold",
        },
      },
      ticks: {
        stepSize: 1,
        callback: function (value) {
          return Math.floor(value);
        },
      },
    },
    x: {
      title: {
        display: true,
        text: "App Name", // ✅ X-axis title
        font: {
          size: 14,
          weight: "bold",
        },
      },
    },
  },
  plugins: {
    tooltip: {
      callbacks: {
        label: function (context) {
          const appName = context.label || "";
          const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
          return `Hits of ${appName} : ${value}`;
        },
      },
    },
    legend: {
      display: false, // ❗ Hides the top legend
    },
  },
};

return <div className="chart-wrapper pm-chart-wrapper">
            {message ? (
                <div style={{
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    width:'100%', 
                    height: '100%', 
                    border: '1px solid #d4d4d4'
                }}>
                    {message}
                </div>
            ) : (
                getChart(data, options, selectedChart)
            )}
        </div>;
}

function getChartColors(count, type) {
  const baseColors = [
      { bg: 'rgba(255, 99, 132, 0.5)', border: 'rgba(255, 99, 132, 1)' },
      { bg: 'rgba(54, 162, 235, 0.5)', border: 'rgba(54, 162, 235, 1)' },
      { bg: 'rgba(255, 206, 86, 0.5)', border: 'rgba(255, 206, 86, 1)' },
      { bg: 'rgba(75, 192, 192, 0.5)', border: 'rgba(75, 192, 192, 1)' },
      { bg: 'rgba(153, 102, 255, 0.5)', border: 'rgba(153, 102, 255, 1)' }
  ];
  
  // Return colors needed, repeating if necessary
  return Array(count).fill().map((_, index) => 
      baseColors[index % baseColors.length][type]
  );
}

export let getBackground = (selectedChart, length) => selectedChart === 'Bar' || selectedChart === 'Line' 
                ? function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) {
                    return 'rgba(54, 162, 235, 0.5)';
                    }
                    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                    gradient.addColorStop(0, 'rgba(15,115,173, 0.4)');
                    gradient.addColorStop(1, 'rgba(66,181,212, 0.8)');
                    return gradient;
                }
                : getChartColors(length, 'bg');

export let getBorder = (selectedChart, length) => selectedChart === 'Line' 
                ? function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) {
                    return 'rgba(54, 162, 235, 1)';
                    }
                    
                    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                    gradient.addColorStop(0, 'rgba(66,181,212, 0.8)');
                    gradient.addColorStop(1, 'rgba(66,181,212, 1)');
                    return gradient;
                }
                : getChartColors(length, 'border');