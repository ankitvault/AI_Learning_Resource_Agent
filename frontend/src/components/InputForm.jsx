import React from 'react';

function InputForm({ onSubmit, loading }) {
  const [formData, setFormData] = React.useState({
    board: 'CBSE',
    class_level: '10',
    subject: '',
    topic: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.subject.trim() || !formData.topic.trim()) {
      alert('Please fill in both Subject and Topic.');
      return;
    }
    onSubmit(formData);
  };

  return (
    <div className="card form-card">
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="board">Board</label>
            <select
              id="board"
              name="board"
              value={formData.board}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="CBSE">CBSE</option>
              <option value="ICSE">ICSE</option>
              <option value="Maharashtra Board">Maharashtra Board</option>
              <option value="UP Board">UP Board</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="class_level">Class</label>
            <select
              id="class_level"
              name="class_level"
              value={formData.class_level}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="6">6</option>
              <option value="7">7</option>
              <option value="8">8</option>
              <option value="9">9</option>
              <option value="10">10</option>
              <option value="11">11</option>
              <option value="12">12</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="subject">Subject</label>
            <input
              type="text"
              id="subject"
              name="subject"
              placeholder="e.g. Science, Mathematics"
              value={formData.subject}
              onChange={handleChange}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="topic">Topic</label>
            <input
              type="text"
              id="topic"
              name="topic"
              placeholder="e.g. Chemical Reactions and Equations"
              value={formData.topic}
              onChange={handleChange}
              disabled={loading}
              required
            />
          </div>
        </div>

        <button type="submit" className="submit-btn" disabled={loading}>
          {loading ? 'Generating...' : 'Generate Study Pack →'}
        </button>
      </form>
    </div>
  );
}

export default InputForm;
