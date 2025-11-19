import React from 'react';

const DateRangePicker = ({ selectedDate, onChange }) => {
  const [startDate, setStartDate] = React.useState(selectedDate.start);
  const [endDate, setEndDate] = React.useState(selectedDate.end);
    // ksdflk
  return (
    <>
      <div className="date-input-group">
        <label className="date-label">Start Date</label>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              // console.log(startDate, endDate);
              onChange({
                start: startDate,
                end: endDate
              });
            }
          }}
          className="date-input"
        />
      </div>

      <div className="date-input-group">
        <label className="date-label">End Date</label>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              // console.log(startDate, endDate);
              onChange({
                start: startDate,
                end: endDate
              });
            }
          }}
          className="date-input"
        />
      </div>


    </>
  );
};

export default DateRangePicker;