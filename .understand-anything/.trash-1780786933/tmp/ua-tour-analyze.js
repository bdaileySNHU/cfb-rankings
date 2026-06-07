#!/usr/bin/env node
'use strict';

const fs = require('fs');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-tour-analyze.js <input.json> <output.json>');
  process.exit(1);
}

let input;
try {
  input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
} catch (e) {
  console.error('Failed to read/parse input:', e.message);
  process.exit(1);
}

const { nodes, edges, layers } = input;

// Build adjacency structures
const fanInMap = {};   // nodeId -> count of edges pointing TO it
const fanOutMap = {};  // nodeId -> count of edges pointing FROM it
const outEdges = {};   // nodeId -> [targetId]
const inEdges = {};    // nodeId -> [sourceId]

for (const node of nodes) {
  fanInMap[node.id] = 0;
  fanOutMap[node.id] = 0;
  outEdges[node.id] = [];
  inEdges[node.id] = [];
}

for (const edge of edges) {
  if (fanInMap[edge.target] !== undefined) fanInMap[edge.target]++;
  if (fanOutMap[edge.source] !== undefined) fanOutMap[edge.source]++;
  if (outEdges[edge.source]) outEdges[edge.source].push(edge.target);
  if (inEdges[edge.target]) inEdges[edge.target].push(edge.source);
}

// A. Fan-In Ranking
const fanInRanking = nodes
  .map(n => ({ id: n.id, fanIn: fanInMap[n.id] || 0, name: n.name }))
  .sort((a, b) => b.fanIn - a.fanIn)
  .slice(0, 20);

// B. Fan-Out Ranking
const fanOutRanking = nodes
  .map(n => ({ id: n.id, fanOut: fanOutMap[n.id] || 0, name: n.name }))
  .sort((a, b) => b.fanOut - a.fanOut)
  .slice(0, 20);

// C. Entry Point Candidates
const totalNodes = nodes.length;
const fanOutValues = nodes.map(n => fanOutMap[n.id] || 0).sort((a, b) => a - b);
const fanOutTop10Threshold = fanOutValues[Math.floor(totalNodes * 0.9)];
const fanInBottom25Threshold = fanInValues => {
  const sorted = nodes.map(n => fanInMap[n.id] || 0).sort((a, b) => a - b);
  return sorted[Math.floor(totalNodes * 0.25)];
};
const fanInThreshold = fanInBottom25Threshold();

const entryPointNames = new Set([
  'index.ts','index.js','main.ts','main.js','app.ts','app.js',
  'server.ts','server.js','mod.rs','main.go','main.py','main.rs',
  'manage.py','app.py','wsgi.py','asgi.py','run.py','__main__.py',
  'Application.java','Main.java','Program.cs','config.ru','index.php',
  'App.swift','Application.kt','main.cpp','main.c'
]);

function scoreEntryPoint(node) {
  let score = 0;
  if (node.type === 'document') {
    if (node.name === 'README.md' && (!node.filePath || !node.filePath.includes('/'))) {
      score += 5;
    } else if (node.name && node.name.endsWith('.md') && node.filePath && !node.filePath.slice(0, -node.name.length - 1).includes('/')) {
      score += 2;
    }
    return score;
  }
  // code file
  if (entryPointNames.has(node.name)) score += 3;
  // depth check
  const depth = node.filePath ? node.filePath.split('/').length - 1 : 99;
  if (depth <= 1) score += 1;
  if ((fanOutMap[node.id] || 0) >= fanOutTop10Threshold) score += 1;
  if ((fanInMap[node.id] || 0) <= fanInThreshold) score += 1;
  return score;
}

const entryPointCandidates = nodes
  .map(n => ({ id: n.id, score: scoreEntryPoint(n), name: n.name, summary: n.summary || '' }))
  .sort((a, b) => b.score - a.score)
  .slice(0, 5);

// D. BFS from top code entry point
const topCodeEntry = entryPointCandidates.find(c => {
  const node = nodes.find(n => n.id === c.id);
  return node && node.type === 'file';
});

const bfsStart = topCodeEntry ? topCodeEntry.id : null;
let bfsResult = { startNode: bfsStart, order: [], depthMap: {}, byDepth: {} };

if (bfsStart) {
  const visited = new Set();
  const queue = [{ id: bfsStart, depth: 0 }];
  visited.add(bfsStart);

  while (queue.length > 0) {
    const { id, depth } = queue.shift();
    bfsResult.order.push(id);
    bfsResult.depthMap[id] = depth;
    if (!bfsResult.byDepth[depth]) bfsResult.byDepth[depth] = [];
    bfsResult.byDepth[depth].push(id);

    // Follow imports and calls edges
    const neighbors = (outEdges[id] || []).filter(target => {
      const edge = edges.find(e => e.source === id && e.target === target);
      return edge && (edge.type === 'imports' || edge.type === 'calls');
    });

    for (const neighbor of neighbors) {
      if (!visited.has(neighbor) && nodes.find(n => n.id === neighbor)) {
        visited.add(neighbor);
        queue.push({ id: neighbor, depth: depth + 1 });
      }
    }
  }
}

// E. Non-Code File Inventory
const docTypes = new Set(['document']);
const infraTypes = new Set(['service', 'pipeline', 'resource']);
const dataTypes = new Set(['table', 'schema', 'endpoint']);
const configTypes = new Set(['config']);

const nonCodeFiles = {
  documentation: [],
  infrastructure: [],
  data: [],
  config: []
};

for (const node of nodes) {
  const entry = { id: node.id, name: node.name, type: node.type, summary: node.summary || '' };
  if (docTypes.has(node.type)) nonCodeFiles.documentation.push(entry);
  else if (infraTypes.has(node.type)) nonCodeFiles.infrastructure.push(entry);
  else if (dataTypes.has(node.type)) nonCodeFiles.data.push(entry);
  else if (configTypes.has(node.type)) nonCodeFiles.config.push(entry);
}

// F. Tightly Coupled Clusters
const edgeSet = new Set(edges.map(e => `${e.source}|||${e.target}`));
function hasEdge(a, b) { return edgeSet.has(`${a}|||${b}`); }

const biPairs = [];
for (const edge of edges) {
  if (hasEdge(edge.target, edge.source) && edge.source < edge.target) {
    biPairs.push([edge.source, edge.target]);
  }
}

// Build clusters from bidirectional pairs
const clusters = [];
const used = new Set();

for (const [a, b] of biPairs) {
  if (used.has(a) || used.has(b)) continue;
  const cluster = new Set([a, b]);
  used.add(a);
  used.add(b);

  // Expand: find nodes connected to 2+ cluster members
  let expanded = true;
  while (expanded) {
    expanded = false;
    for (const node of nodes) {
      if (cluster.has(node.id) || used.has(node.id)) continue;
      let connections = 0;
      for (const member of cluster) {
        if (hasEdge(node.id, member) || hasEdge(member, node.id)) connections++;
      }
      if (connections >= 2 && cluster.size < 5) {
        cluster.add(node.id);
        used.add(node.id);
        expanded = true;
      }
    }
  }

  // Count edges within cluster
  const clusterArr = Array.from(cluster);
  let edgeCount = 0;
  for (let i = 0; i < clusterArr.length; i++) {
    for (let j = 0; j < clusterArr.length; j++) {
      if (i !== j && hasEdge(clusterArr[i], clusterArr[j])) edgeCount++;
    }
  }
  clusters.push({ nodes: clusterArr, edgeCount });
}

clusters.sort((a, b) => b.edgeCount - a.edgeCount);
const topClusters = clusters.slice(0, 10);

// G. Layer List
const layerData = {
  count: layers.length,
  list: layers.map(l => ({ id: l.id, name: l.name, description: l.description }))
};

// H. Node Summary Index
const nodeSummaryIndex = {};
for (const node of nodes) {
  nodeSummaryIndex[node.id] = {
    name: node.name,
    type: node.type,
    summary: node.summary || ''
  };
}

const output = {
  scriptCompleted: true,
  entryPointCandidates,
  fanInRanking,
  fanOutRanking,
  bfsTraversal: bfsResult,
  nonCodeFiles,
  clusters: topClusters,
  layers: layerData,
  nodeSummaryIndex,
  totalNodes: nodes.length,
  totalEdges: edges.length
};

try {
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.log('Analysis complete. Written to', outputPath);
  process.exit(0);
} catch (e) {
  console.error('Failed to write output:', e.message);
  process.exit(1);
}
