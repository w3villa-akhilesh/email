import React, { useState } from 'react';
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const weekLabels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const agentData = {
  'Triage Agent': [12, 19, 3, 5, 2, 3, 7],
  'Pm Agent': [5, 6, 8, 3, 7, 10, 4],
};

const AgentWeekChart = () => {
  const [selectedAgent, setSelectedAgent] = useState('All');

  const datasets =
    selectedAgent === 'All'
      ? Object.entries(agentData).map(([agent, data], i) => ({
          label: agent,
          data,
          backgroundColor: `hsl(${i * 90}, 70%, 60%)`,
        }))
      : [
          {
            label: selectedAgent,
            data: agentData[selectedAgent],
            backgroundColor: 'rgba(75, 192, 192, 0.7)',
          },
        ];

  const chartData = {
    labels: weekLabels,
    datasets,
  };

  const chartOptions = {
    indexAxis: 'y', // horizontal bars
    responsive: true,
    scales: {
      x: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Sessions',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Week Days',
        },
      },
    },
    plugins: {
      legend: {
        position: 'top',
      },
    },
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h3>Weekly Report</h3>

      <select
        onChange={(e) => setSelectedAgent(e.target.value)}
        value={selectedAgent}
        style={{ marginBottom: '16px', padding: '6px' }}
      >
        <option value="All">All Agents</option>
        {Object.keys(agentData).map((agent) => (
          <option key={agent} value={agent}>
            {agent}
          </option>
        ))}
      </select>

      <Bar data={chartData} options={chartOptions} />
    </div>
  );
};

export default AgentWeekChart;
