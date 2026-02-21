// ============================================================
// GraphMind — Static Mock Data
// Used ONLY as offline fallback when the backend is unreachable.
// Real data is fetched exclusively from the backend/ API.
// ============================================================

// ---- Chat responses (offline fallback) ----
const CHAT_RESPONSES = {
  user_1: [
    {
      trigger: ['quantum', 'qubit', 'superposition', 'entanglement'],
      response: 'Quantum computing leverages quantum-mechanical phenomena such as **superposition** and **entanglement** to process information. A **qubit**, unlike a classical bit, can exist in a superposition of states (|0⟩ and |1⟩ simultaneously), enabling quantum computers to explore multiple solutions in parallel. Entanglement creates correlations between qubits that persist regardless of distance, which is fundamental to quantum speedup.',
      retrieval_time_ms: 47,
      memory_citations: [
        { node_id: 'n1', title: 'Quantum Computing', snippet: 'Study of computation using quantum-mechanical phenomena' },
        { node_id: 'n2', title: 'Qubit', snippet: 'Basic unit of quantum information' },
        { node_id: 'n3', title: 'Superposition', snippet: 'A qubit can exist in multiple states simultaneously' },
        { node_id: 'n4', title: 'Entanglement', snippet: 'Quantum entanglement links qubits across distance' },
      ],
    },
    {
      trigger: ['neural', 'network', 'transformer', 'backpropagation', 'deep learning'],
      response: 'Neural networks are computing systems inspired by biological neural networks. Modern architectures like the **Transformer** have revolutionized natural language processing through attention mechanisms. Training these networks relies on **backpropagation**, an algorithm that computes gradients to update weights iteratively, minimizing the loss function across the network layers.',
      retrieval_time_ms: 32,
      memory_citations: [
        { node_id: 'n5', title: 'Neural Networks', snippet: 'Computing systems inspired by biological neural networks' },
        { node_id: 'n6', title: 'Transformer', snippet: 'Attention-based architecture revolutionizing NLP' },
        { node_id: 'n7', title: 'Backpropagation', snippet: 'Algorithm for training neural networks' },
      ],
    },
    {
      trigger: ['graph', 'neo4j', 'cypher', 'database', 'knowledge'],
      response: 'Graph databases like **Neo4j** use graph structures with nodes, edges, and properties to represent and store data. They are queried using **Cypher**, a declarative graph query language. This approach is ideal for building **knowledge graphs** that capture complex relationships between entities, enabling powerful semantic queries and pattern matching across interconnected data.',
      retrieval_time_ms: 28,
      memory_citations: [
        { node_id: 'n8', title: 'Graph Databases', snippet: 'Database using graph structures for semantic queries' },
        { node_id: 'n9', title: 'Neo4j', snippet: 'Leading native graph database platform' },
        { node_id: 'n10', title: 'Cypher Query Language', snippet: 'Declarative graph query language for Neo4j' },
        { node_id: 'n11', title: 'Knowledge Graph', snippet: 'Graph-based knowledge representation' },
      ],
    },
  ],
  user_2: [
    {
      trigger: ['climate', 'warming', 'temperature', 'co2', 'carbon', 'emission'],
      response: 'Climate change refers to long-term shifts in global temperatures and weather patterns. Human activities, particularly **CO₂ emissions**, are the primary driver since the 1800s. The Paris Agreement established the **1.5°C target** to limit global warming. Current projections show continued **sea level rise** of approximately 3.6mm per year, threatening coastal communities worldwide.',
      retrieval_time_ms: 41,
      memory_citations: [
        { node_id: 'n1', title: 'Climate Change', snippet: 'Long-term shifts in global temperatures and weather patterns' },
        { node_id: 'n2', title: 'CO₂ Emissions', snippet: 'Primary greenhouse gas from human activities' },
        { node_id: 'n3', title: '1.5°C Target', snippet: 'Paris Agreement goal to limit warming' },
        { node_id: 'n4', title: 'Sea Level Rise', snippet: 'Global sea levels rising ~3.6mm per year' },
      ],
    },
    {
      trigger: ['renewable', 'solar', 'wind', 'energy', 'power', 'storage'],
      response: 'Renewable energy comes from naturally replenishing sources. **Solar power** converts sunlight to electricity via photovoltaic cells, while **wind energy** harnesses kinetic energy from air currents. Both require robust **energy storage** solutions (like lithium-ion batteries) to handle intermittent generation. The global goal of becoming **carbon neutral by 2050** depends heavily on scaling these technologies.',
      retrieval_time_ms: 35,
      memory_citations: [
        { node_id: 'n5', title: 'Renewable Energy', snippet: 'Energy from naturally replenishing sources' },
        { node_id: 'n6', title: 'Solar Power', snippet: 'Energy from sunlight using photovoltaic cells' },
        { node_id: 'n7', title: 'Wind Energy', snippet: 'Kinetic energy from wind converted to electricity' },
        { node_id: 'n9', title: 'Energy Storage', snippet: 'Battery systems for storing renewable energy' },
      ],
    },
  ],
};

// Fallback response for irrelevant queries
const FALLBACK_RESPONSE = {
  response: "I don't have information about that topic in my memory. The available knowledge base doesn't contain relevant data to answer this question accurately. Please try asking about topics that have been ingested into the system.",
  retrieval_time_ms: 12,
  memory_citations: [],
};

/**
 * Simulate a chat API call.
 * Matches query keywords against known triggers; returns fallback otherwise.
 */
export function simulateChatResponse(userId, query) {
  const userResponses = CHAT_RESPONSES[userId] || [];
  const lowerQuery = query.toLowerCase();

  for (const resp of userResponses) {
    const matched = resp.trigger.some((keyword) => lowerQuery.includes(keyword));
    if (matched) {
      return {
        response: resp.response,
        retrieval_time_ms: resp.retrieval_time_ms + Math.floor(Math.random() * 15),
        memory_citations: resp.memory_citations,
      };
    }
  }

  return {
    ...FALLBACK_RESPONSE,
    retrieval_time_ms: FALLBACK_RESPONSE.retrieval_time_ms + Math.floor(Math.random() * 8),
  };
}

/**
 * Simulate ingesting a new document.
 * Returns a fake ingestion result.
 */
export function simulateIngest(userId, title, content) {
  const fakeChunks = Math.floor(content.length / 120) + 1;
  return {
    id: `doc_${Date.now()}`,
    title,
    type: 'text',
    ingestedAt: new Date().toISOString(),
    chunks: fakeChunks,
    nodesCreated: Math.ceil(fakeChunks / 2),
    edgesCreated: Math.ceil(fakeChunks / 3),
  };
}
