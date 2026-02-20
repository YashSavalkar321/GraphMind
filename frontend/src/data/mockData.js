// ============================================================
// GraphMind — Static Mock Data
// All backend API responses are simulated here.
// When the real backend is ready, replace these with fetch calls.
// ============================================================

// ---- Users ----
export const USERS = [
  {
    id: 'user_1',
    name: 'Alice Morgan',
    avatar: 'AM',
    color: '#6366f1',
  },
  {
    id: 'user_2',
    name: 'Bob Chen',
    avatar: 'BC',
    color: '#0ea5e9',
  },
];

// ---- Ingested Documents per user ----
export const INGESTED_DOCS = {
  user_1: [
    { id: 'doc_1', title: 'Quantum Computing Basics', type: 'pdf', ingestedAt: '2026-02-15T10:30:00Z', chunks: 12 },
    { id: 'doc_2', title: 'Neural Network Architectures', type: 'text', ingestedAt: '2026-02-16T14:22:00Z', chunks: 8 },
    { id: 'doc_3', title: 'Graph Database Overview', type: 'pdf', ingestedAt: '2026-02-17T09:15:00Z', chunks: 15 },
  ],
  user_2: [
    { id: 'doc_4', title: 'Climate Change Report 2026', type: 'pdf', ingestedAt: '2026-02-14T11:00:00Z', chunks: 20 },
    { id: 'doc_5', title: 'Renewable Energy Sources', type: 'text', ingestedAt: '2026-02-15T16:45:00Z', chunks: 10 },
  ],
};

// ---- Mindmap / Graph data per user ----
export const MINDMAP_DATA = {
  user_1: {
    nodes: [
      { id: 'n1', type: 'concept', data: { label: 'Quantum Computing', description: 'Study of computation using quantum-mechanical phenomena', nodeType: 'concept', docSource: 'doc_1' }, position: { x: 400, y: 50 } },
      { id: 'n2', type: 'entity', data: { label: 'Qubit', description: 'Basic unit of quantum information', nodeType: 'entity', docSource: 'doc_1' }, position: { x: 150, y: 200 } },
      { id: 'n3', type: 'entity', data: { label: 'Superposition', description: 'A qubit can exist in multiple states simultaneously', nodeType: 'entity', docSource: 'doc_1' }, position: { x: 650, y: 200 } },
      { id: 'n4', type: 'fact', data: { label: 'Entanglement', description: 'Quantum entanglement links qubits across distance', nodeType: 'fact', docSource: 'doc_1' }, position: { x: 400, y: 350 } },
      { id: 'n5', type: 'concept', data: { label: 'Neural Networks', description: 'Computing systems inspired by biological neural networks', nodeType: 'concept', docSource: 'doc_2' }, position: { x: 900, y: 50 } },
      { id: 'n6', type: 'entity', data: { label: 'Transformer', description: 'Attention-based architecture revolutionizing NLP', nodeType: 'entity', docSource: 'doc_2' }, position: { x: 800, y: 250 } },
      { id: 'n7', type: 'entity', data: { label: 'Backpropagation', description: 'Algorithm for training neural networks', nodeType: 'entity', docSource: 'doc_2' }, position: { x: 1050, y: 250 } },
      { id: 'n8', type: 'concept', data: { label: 'Graph Databases', description: 'Database using graph structures for semantic queries', nodeType: 'concept', docSource: 'doc_3' }, position: { x: 150, y: 450 } },
      { id: 'n9', type: 'document', data: { label: 'Neo4j', description: 'Leading native graph database platform', nodeType: 'document', docSource: 'doc_3' }, position: { x: 50, y: 600 } },
      { id: 'n10', type: 'fact', data: { label: 'Cypher Query Language', description: 'Declarative graph query language for Neo4j', nodeType: 'fact', docSource: 'doc_3' }, position: { x: 300, y: 600 } },
      { id: 'n11', type: 'entity', data: { label: 'Knowledge Graph', description: 'Graph-based knowledge representation', nodeType: 'entity', docSource: 'doc_3' }, position: { x: 550, y: 500 } },
      { id: 'n12', type: 'fact', data: { label: 'Quantum Speedup', description: 'Exponential speedup for certain algorithms', nodeType: 'fact', docSource: 'doc_1' }, position: { x: 200, y: 350 } },
    ],
    edges: [
      { id: 'e1-2', source: 'n1', target: 'n2', label: 'uses', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e1-3', source: 'n1', target: 'n3', label: 'relies on', style: { stroke: '#6366f1' } },
      { id: 'e1-4', source: 'n1', target: 'n4', label: 'exploits', style: { stroke: '#6366f1' } },
      { id: 'e2-4', source: 'n2', target: 'n4', label: 'enables', animated: true, style: { stroke: '#8b5cf6' } },
      { id: 'e1-12', source: 'n1', target: 'n12', label: 'achieves', style: { stroke: '#10b981' } },
      { id: 'e5-6', source: 'n5', target: 'n6', label: 'includes', style: { stroke: '#0ea5e9' } },
      { id: 'e5-7', source: 'n5', target: 'n7', label: 'trained by', style: { stroke: '#0ea5e9' } },
      { id: 'e8-9', source: 'n8', target: 'n9', label: 'example', animated: true, style: { stroke: '#6366f1' } },
      { id: 'e8-10', source: 'n8', target: 'n10', label: 'queried with', style: { stroke: '#6366f1' } },
      { id: 'e8-11', source: 'n8', target: 'n11', label: 'implements', style: { stroke: '#8b5cf6' } },
      { id: 'e11-5', source: 'n11', target: 'n5', label: 'enhances', animated: true, style: { stroke: '#10b981' } },
      { id: 'e3-12', source: 'n3', target: 'n12', label: 'contributes to', style: { stroke: '#8b5cf6' } },
    ],
  },
  user_2: {
    nodes: [
      { id: 'n1', type: 'concept', data: { label: 'Climate Change', description: 'Long-term shifts in global temperatures and weather patterns', nodeType: 'concept', docSource: 'doc_4' }, position: { x: 400, y: 50 } },
      { id: 'n2', type: 'entity', data: { label: 'CO₂ Emissions', description: 'Primary greenhouse gas from human activities', nodeType: 'entity', docSource: 'doc_4' }, position: { x: 150, y: 200 } },
      { id: 'n3', type: 'fact', data: { label: '1.5°C Target', description: 'Paris Agreement goal to limit warming', nodeType: 'fact', docSource: 'doc_4' }, position: { x: 650, y: 200 } },
      { id: 'n4', type: 'entity', data: { label: 'Sea Level Rise', description: 'Global sea levels rising ~3.6mm per year', nodeType: 'entity', docSource: 'doc_4' }, position: { x: 400, y: 350 } },
      { id: 'n5', type: 'concept', data: { label: 'Renewable Energy', description: 'Energy from naturally replenishing sources', nodeType: 'concept', docSource: 'doc_5' }, position: { x: 850, y: 50 } },
      { id: 'n6', type: 'document', data: { label: 'Solar Power', description: 'Energy from sunlight using photovoltaic cells', nodeType: 'document', docSource: 'doc_5' }, position: { x: 750, y: 250 } },
      { id: 'n7', type: 'document', data: { label: 'Wind Energy', description: 'Kinetic energy from wind converted to electricity', nodeType: 'document', docSource: 'doc_5' }, position: { x: 1000, y: 250 } },
      { id: 'n8', type: 'fact', data: { label: 'Carbon Neutral by 2050', description: 'Global goal to achieve net-zero emissions', nodeType: 'fact', docSource: 'doc_4' }, position: { x: 200, y: 450 } },
      { id: 'n9', type: 'entity', data: { label: 'Energy Storage', description: 'Battery systems for storing renewable energy', nodeType: 'entity', docSource: 'doc_5' }, position: { x: 900, y: 400 } },
    ],
    edges: [
      { id: 'e1-2', source: 'n1', target: 'n2', label: 'caused by', animated: true, style: { stroke: '#ef4444' } },
      { id: 'e1-3', source: 'n1', target: 'n3', label: 'addressed by', style: { stroke: '#10b981' } },
      { id: 'e1-4', source: 'n1', target: 'n4', label: 'causes', style: { stroke: '#ef4444' } },
      { id: 'e5-6', source: 'n5', target: 'n6', label: 'includes', animated: true, style: { stroke: '#0ea5e9' } },
      { id: 'e5-7', source: 'n5', target: 'n7', label: 'includes', style: { stroke: '#0ea5e9' } },
      { id: 'e5-1', source: 'n5', target: 'n1', label: 'mitigates', animated: true, style: { stroke: '#10b981' } },
      { id: 'e2-8', source: 'n2', target: 'n8', label: 'targeted by', style: { stroke: '#f59e0b' } },
      { id: 'e5-9', source: 'n5', target: 'n9', label: 'requires', style: { stroke: '#0ea5e9' } },
    ],
  },
};

// ---- Chat responses (simulated AI answers) ----
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
