import React from 'react';
import SectionCard from './SectionCard.jsx';

function StudyPack({ data }) {
  if (!data) return null;

  const {
    what_to_learn = [],
    question_papers = [],
    marking_schemes = [],
    topic_summary = {},
    videos = [],
    notes_links = []
  } = data;

  return (
    <div className="study-pack">
      {/* SECTION 4: Topic Summary (Let's show this early to build context) */}
      <section className="pack-section">
        <h3 className="section-title">Topic Summary</h3>
        <div className="summary-card">
          <p className="summary-overview">{topic_summary.overview}</p>
          
          {topic_summary.key_concepts && topic_summary.key_concepts.length > 0 && (
            <div className="summary-sub">
              <h4>Key Concepts</h4>
              <div className="pills-container">
                {topic_summary.key_concepts.map((concept, index) => (
                  <span key={index} className="pill concept-pill">{concept}</span>
                ))}
              </div>
            </div>
          )}

          {topic_summary.important_formulas && topic_summary.important_formulas.length > 0 && (
            <div className="summary-sub">
              <h4>Important Formulas / Facts</h4>
              <div className="pills-container">
                {topic_summary.important_formulas.map((formula, index) => (
                  <span key={index} className="pill formula-pill">{formula}</span>
                ))}
              </div>
            </div>
          )}

          {topic_summary.common_mistakes && topic_summary.common_mistakes.length > 0 && (
            <div className="summary-sub">
              <h4>Common Mistakes to Avoid</h4>
              <ul className="mistakes-list">
                {topic_summary.common_mistakes.map((mistake, index) => (
                  <li key={index}>{mistake}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      {/* SECTION 1: What to Learn */}
      {what_to_learn && what_to_learn.length > 0 && (
        <section className="pack-section">
          <h3 className="section-title">What to Learn</h3>
          <div className="card list-card">
            <ul className="learning-points">
              {what_to_learn.map((point, index) => (
                <li key={index}>{point}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* SECTION 5: Videos */}
      {videos && videos.length > 0 && (
        <section className="pack-section">
          <h3 className="section-title">Recommended Videos</h3>
          <div className="cards-grid">
            {videos.map((vid, index) => (
              <SectionCard
                key={index}
                title={vid.title}
                subtitle={vid.channel}
                url={vid.url}
                description={vid.why}
                badge="Video"
                verified={vid.verified}
                is_search_fallback={vid.is_search_fallback}
              />
            ))}
          </div>
        </section>
      )}

      {/* SECTION 6: Notes & Resources */}
      {notes_links && notes_links.length > 0 && (
        <section className="pack-section">
          <h3 className="section-title">Notes & Study Resources</h3>
          <div className="cards-grid">
            {notes_links.map((note, index) => (
              <SectionCard
                key={index}
                title={note.title}
                subtitle={note.source}
                url={note.url}
                badge={note.type || 'Resource'}
                verified={note.verified}
                is_search_fallback={note.is_search_fallback}
              />
            ))}
          </div>
        </section>
      )}

      {/* SECTION 2: Question Papers */}
      {question_papers && question_papers.length > 0 && (
        <section className="pack-section">
          <h3 className="section-title">Question Papers</h3>
          <div className="cards-grid">
            {question_papers.map((paper, index) => (
              <SectionCard
                key={index}
                title={paper.title}
                subtitle={paper.source}
                url={paper.url}
                badge="Paper"
                verified={paper.verified}
                is_search_fallback={paper.is_search_fallback}
              />
            ))}
          </div>
        </section>
      )}

      {/* SECTION 3: Marking Schemes */}
      {marking_schemes && marking_schemes.length > 0 && (
        <section className="pack-section">
          <h3 className="section-title">Marking Schemes</h3>
          <div className="cards-grid">
            {marking_schemes.map((scheme, index) => (
              <SectionCard
                key={index}
                title={scheme.title}
                subtitle={scheme.source}
                url={scheme.url}
                badge="Scheme"
                verified={scheme.verified}
                is_search_fallback={scheme.is_search_fallback}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default StudyPack;
