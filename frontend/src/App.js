import React, { useState } from "react";
import axios from "axios";

const App = () => {
  const [file, setFile] = useState(null);
  const [summary, setSummary] = useState("");
  const [bullets, setBullets] = useState("");
  const [faq, setFaq] = useState("");
  const [keywords, setKeywords] = useState([]);
  const [citations, setCitations] = useState([]);
  const [readability, setReadability] = useState("");
  const [language, setLanguage] = useState("en");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please upload a file.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);

    try {
      const response = await axios.post("http://127.0.0.1:8000/summarize/", formData);
      setSummary(response.data.summary);
      setBullets(response.data.bullets);
      setFaq(response.data.faq);
      setKeywords(response.data.keywords);
      setCitations(response.data.citations);
      setReadability(response.data.readability_score);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Error processing file.");
    }
    setLoading(false);
  };

  const handleAskQuestion = async () => {
    if (!file || !question) {
      alert("Please upload a file and enter a question.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("question", question);

    try {
      const response = await axios.post("http://127.0.0.1:8000/ask/", formData);
      setAnswer(response.data.answer);
    } catch (error) {
      console.error("Error asking question:", error);
      alert("Error processing question.");
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>Legal Document Summarizer</h1>

      <input type="file" onChange={handleFileChange} />
      <br />
      <label>Choose Language:</label>
      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option value="en">English</option>
        <option value="hi">Hindi</option>
        <option value="fr">French</option>
        <option value="es">Spanish</option>
      </select>
      <br />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Processing..." : "Upload & Summarize"}
      </button>

      {summary && (
        <div>
          <h2>Summary:</h2>
          <p dangerouslySetInnerHTML={{ __html: summary }}></p>

          <h2>Bullet Points:</h2>
          <pre>{bullets}</pre>

          <h2>FAQs:</h2>
          <pre>{faq}</pre>

          <h3>Keywords:</h3>
          <p>{keywords.join(", ")}</p>

          <h3>Citations:</h3>
          <p>{citations.join(", ")}</p>

          <h3>Readability Score:</h3>
          <p>{readability}</p>

          <h2>Ask a Question:</h2>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a legal question..."
          />
          <button onClick={handleAskQuestion}>Ask</button>
          {answer && (
            <div>
              <h3>Answer:</h3>
              <p>{answer}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default App;
