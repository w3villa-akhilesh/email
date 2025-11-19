import React, { useState, useEffect, useRef } from "react";
import { getBorder, showChart } from "./getChart";
import { faCalendarDays } from "@fortawesome/free-solid-svg-icons";
import { DateRange } from "react-date-range";
import { format } from "date-fns";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { CharLogData } from "../../Api/Auth";

export function LogChartStatic() {
    // const today = new Date();
    // const oneWeekAgo = new Date();
    // oneWeekAgo.setDate(today.getDate() - 6);

    // const formattedToday = today.toISOString().split("T")[0];
    // const formattedOneWeekAgo = oneWeekAgo.toISOString().split("T")[0];

    // const [dateRange, setDateRange] = useState({
    //     start: formattedOneWeekAgo,
    //     end: formattedToday
    // });

    // const [selectionRange, setSelectionRange] = useState({
    //     startDate: oneWeekAgo,
    //     endDate: today,
    //     key: 'selection'
    // });
    const today = new Date();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);

    const formattedToday = today.toISOString().split("T")[0];
    const formattedMonthStart = monthStart.toISOString().split("T")[0];

    const [dateRange, setDateRange] = useState({
        start: formattedMonthStart,
        end: formattedToday
    });

    const [selectionRange, setSelectionRange] = useState({
        startDate: monthStart,
        endDate: today,
        key: 'selection'
    });

    const [selectedApp, setSelectedApp] = useState("");
    const [chartType, setChartType] = useState("Bar");
    const [openDateRange, setOpenDateRange] = useState(false);
    const [chartData, setChartData] = useState(null);
    const refOne = useRef();

    const toggleDateRange = () => {
        setOpenDateRange(prev => !prev);
    };

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (refOne.current && !refOne.current.contains(event.target)) {
                setOpenDateRange(false);
            }
        };

        if (openDateRange) {
            document.addEventListener('mousedown', handleClickOutside);
        } else {
            document.removeEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [openDateRange]);

    const formatAppName = (name) => {
        return name
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    };

    const fetchData = async () => {
        try {
            const token = localStorage.getItem('access_token');

            const params = {
                app_name: selectedApp || '',
                start_date: dateRange.start,
                end_date: dateRange.end
            };

            const response = await CharLogData(token, params);
            const dailyData = response.apps;

            const appNames = dailyData.map(app => formatAppName(app.app_name));
            const totalHits = dailyData.map(app => app.total_hits);

            const colors = [
                '#FF5733', '#DAF7A6', '#C70039', '#900C3F', '#581845'
            ];

            setChartData({
                labels: appNames,
                datasets: [
                    {
                        label: appNames,
                        data: totalHits,
                        backgroundColor: colors,
                        borderColor: getBorder(chartType, totalHits.length),
                    }
                ]
            });
        } catch (error) {
            console.error("Error fetching data:", error);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedApp, chartType, dateRange]);

    const handleDateRange = (range) => {
        setSelectionRange(range.selection);
        setDateRange({
            start: format(range.selection.startDate, 'yyyy-MM-dd'),
            end: format(range.selection.endDate, 'yyyy-MM-dd')
        });
    };

    return (
        <div className="chart-dashboard">
            <div className="controls-container" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginBottom: '20px' }}>

                <div className="calenderWarp me-3">
                    <input
                        readOnly
                        value={`${format(selectionRange.startDate, "MM/dd/yyyy")} to ${format(selectionRange.endDate, "MM/dd/yyyy")}`}
                        onClick={toggleDateRange}
                        className="inputBox"
                    />
                    <span className="date-icon">
                        <FontAwesomeIcon className="font-20" icon={faCalendarDays} />
                    </span>

                    {openDateRange && (
                        <div ref={refOne}>
                            <DateRange
                                ranges={[selectionRange]}
                                onChange={handleDateRange}
                                editableDateInputs={true}
                                moveRangeOnFirstSelection={false}
                                months={1}
                                direction="vertical"
                                className="calendarElement"
                                maxDate={new Date()}
                            />
                        </div>
                    )}
                </div>
            </div>

            <div className="chart-container">
                {chartData && chartData.datasets && chartData.datasets[0].data.length > 0 ? (
                    showChart(chartData, chartType, null) // Assuming `showChart` is the function that renders the chart
                ) : (
                    <div style={{ textAlign: 'center', color: 'gray', fontStyle: 'italic', marginTop: '20px' }}>
                        No data found
                    </div>
                )}
            </div>

        </div>
    );
}
