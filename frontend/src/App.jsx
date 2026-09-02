import React, { useState } from 'react';
import InputForm from './components/InputForm.jsx';
import StudyPack from './components/StudyPack.jsx';
import Loader from './components/Loader.jsx';

function App() {
  const [apiResponse, setApiResponse] = useState(null);
  const [activeTab, setActiveTab] = useState('response1');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setApiResponse(null);

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        let errText = 'Failed to generate study pack.';
        try {
          const errJson = await response.json();
          if (errJson.detail) errText = errJson.detail;
        } catch (e) {
          errText = `Server error: ${response.statusText}`;
        }
        throw new Error(errText);
      }

      const data = await response.json();
      setApiResponse(data);
      if (data.response1) {
        setActiveTab('response1');
      } else if (data.response2) {
        setActiveTab('response2');
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred while communicating with the server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>AI Study Resource Agent</h1>
        <p>Generate reliable, web-researched study packs for Indian school exams.</p>
      </header>

      <main className="app-main">
        <InputForm onSubmit={handleSubmit} loading={loading} />

        {loading && <Loader />}

        {error && (
          <div className="error-message">
            <h4>Error generating study pack</h4>
            <p>{error}</p>
          </div>
        )}

        {apiResponse && (
          <div className="responses-container">
            <div className="tabs">
              {apiResponse.response1 && (
                <button 
                  className={`tab-btn ${activeTab === 'response1' ? 'active' : ''}`}
                  onClick={() => setActiveTab('response1')}
                >
                  Response 1 (Groq)
                </button>
              )}
              {apiResponse.response2 && (
                <button 
                  className={`tab-btn ${activeTab === 'response2' ? 'active' : ''}`}
                  onClick={() => setActiveTab('response2')}
                >
                  Response 2 (Gemini)
                </button>
              )}
            </div>
            
            <div className="tab-content">
              {activeTab === 'response1' && apiResponse.response1 && <StudyPack data={apiResponse.response1} />}
              {activeTab === 'response2' && apiResponse.response2 && <StudyPack data={apiResponse.response2} />}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
