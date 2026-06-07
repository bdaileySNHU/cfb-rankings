const fs = require('fs');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-arch-analyze.js <input.json> <output.json>');
  process.exit(1);
}

const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const { fileNodes, importEdges, allEdges } = input;

// A. Directory Grouping
function getFilePath(node) {
  return node.filePath || node.id.replace(/^[^:]+:/, '');
}

function getTopDir(filePath) {
  const parts = filePath.split('/');
  return parts.length > 1 ? parts[0] : 'root';
}

const directoryGroups = {};
fileNodes.forEach(n => {
  const fp = getFilePath(n);
  const dir = getTopDir(fp);
  directoryGroups[dir] = directoryGroups[dir] || [];
  directoryGroups[dir].push(n.id);
});

// B. Node Type Grouping
const nodeTypeGroups = {};
fileNodes.forEach(n => {
  const t = n.type || 'file';
  nodeTypeGroups[t] = nodeTypeGroups[t] || [];
  nodeTypeGroups[t].push(n.id);
});

// C. Import Adjacency
const fanIn = {};
const fanOut = {};
importEdges.forEach(e => {
  fanOut[e.source] = (fanOut[e.source] || 0) + 1;
  fanIn[e.target] = (fanIn[e.target] || 0) + 1;
});

// D. Cross-Category Dependency Analysis (only file-level edges)
const nodeTypeMap = {};
fileNodes.forEach(n => { nodeTypeMap[n.id] = n.type || 'file'; });

const crossCategoryMap = {};
allEdges.forEach(e => {
  const srcType = nodeTypeMap[e.source];
  const tgtType = nodeTypeMap[e.target];
  if (!srcType || !tgtType) return;
  const key = `${srcType}::${tgtType}::${e.type}`;
  crossCategoryMap[key] = (crossCategoryMap[key] || 0) + 1;
});

const crossCategoryEdges = Object.entries(crossCategoryMap).map(([key, count]) => {
  const [fromType, toType, edgeType] = key.split('::');
  return { fromType, toType, edgeType, count };
});

// E. Inter-Group Import Frequency
const nodeGroupMap = {};
fileNodes.forEach(n => {
  const fp = getFilePath(n);
  nodeGroupMap[n.id] = getTopDir(fp);
});

const interGroupMap = {};
importEdges.forEach(e => {
  const fromGroup = nodeGroupMap[e.source];
  const toGroup = nodeGroupMap[e.target];
  if (!fromGroup || !toGroup || fromGroup === toGroup) return;
  const key = `${fromGroup}->${toGroup}`;
  interGroupMap[key] = (interGroupMap[key] || 0) + 1;
});

const interGroupImports = Object.entries(interGroupMap).map(([key, count]) => {
  const [from, to] = key.split('->');
  return { from, to, count };
}).sort((a, b) => b.count - a.count);

// F. Intra-Group Import Density
const groupEdgeCounts = {};
importEdges.forEach(e => {
  const fromGroup = nodeGroupMap[e.source];
  const toGroup = nodeGroupMap[e.target];
  if (!fromGroup || !toGroup) return;
  groupEdgeCounts[fromGroup] = groupEdgeCounts[fromGroup] || { internal: 0, total: 0 };
  groupEdgeCounts[toGroup] = groupEdgeCounts[toGroup] || { internal: 0, total: 0 };
  groupEdgeCounts[fromGroup].total++;
  groupEdgeCounts[toGroup].total++;
  if (fromGroup === toGroup) {
    groupEdgeCounts[fromGroup].internal++;
  }
});

const intraGroupDensity = {};
Object.entries(groupEdgeCounts).forEach(([group, counts]) => {
  intraGroupDensity[group] = {
    internalEdges: counts.internal,
    totalEdges: counts.total,
    density: counts.total > 0 ? counts.internal / counts.total : 0
  };
});

// G. Directory Pattern Matching
const dirPatterns = {
  routes: 'api', api: 'api', controllers: 'api', endpoints: 'api', handlers: 'api',
  serializers: 'api', blueprints: 'api', routers: 'api', controller: 'api',
  services: 'service', core: 'service', lib: 'service', domain: 'service', logic: 'service',
  composables: 'service', signals: 'service', mailers: 'service', jobs: 'service', channels: 'service',
  internal: 'service',
  models: 'data', db: 'data', data: 'data', persistence: 'data', repository: 'data',
  entities: 'data', migrations: 'data', entity: 'data', sql: 'data', database: 'data', schema: 'data',
  components: 'ui', views: 'ui', pages: 'ui', ui: 'ui', layouts: 'ui', screens: 'ui',
  middleware: 'middleware', plugins: 'middleware', interceptors: 'middleware', guards: 'middleware',
  utils: 'utility', helpers: 'utility', common: 'utility', shared: 'utility', tools: 'utility',
  pkg: 'utility', templatetags: 'utility',
  config: 'config', constants: 'config', env: 'config', settings: 'config',
  management: 'config', commands: 'config',
  '__tests__': 'test', test: 'test', tests: 'test', spec: 'test', specs: 'test',
  types: 'types', interfaces: 'types', schemas: 'types', contracts: 'types', dtos: 'types',
  dto: 'types', request: 'types', response: 'types',
  hooks: 'hooks',
  store: 'state', state: 'state', reducers: 'state', actions: 'state', slices: 'state',
  assets: 'assets', static: 'assets', public: 'assets',
  docs: 'documentation', documentation: 'documentation', wiki: 'documentation',
  deploy: 'infrastructure', deployment: 'infrastructure', infra: 'infrastructure', infrastructure: 'infrastructure',
  k8s: 'infrastructure', kubernetes: 'infrastructure', helm: 'infrastructure', charts: 'infrastructure',
  terraform: 'infrastructure', tf: 'infrastructure', docker: 'infrastructure',
  '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd',
  bin: 'entry', cmd: 'entry',
  diagnostics: 'utility',
  scripts: 'utility',
  utilities: 'utility',
  src: 'service',
  frontend: 'ui',
  '.bmad-core': 'documentation',
  '.claude': 'documentation',
  '.coveragerc': 'config',
};

const patternMatches = {};
Object.keys(directoryGroups).forEach(dir => {
  patternMatches[dir] = dirPatterns[dir] || 'utility';
});

// H. Deployment Topology Detection
const infraPatterns = [/^deploy\//, /Dockerfile/, /docker-compose/, /\.service$/, /\.timer$/, /nginx\.conf/];
const ciPatterns = [/\.github\/workflows/, /\.gitlab-ci\.yml/, /Jenkinsfile/];
const k8sPatterns = [/k8s\//, /kubernetes\//, /\.yaml.*k8s/];
const terraformPatterns = [/\.tf$/, /\.tfvars$/];

const infraFiles = [];
let hasDockerfile = false, hasCompose = false, hasK8s = false, hasTerraform = false, hasCI = false;

fileNodes.forEach(n => {
  const fp = getFilePath(n);
  if (/Dockerfile/.test(fp)) { hasDockerfile = true; infraFiles.push(fp); }
  if (/docker-compose/.test(fp)) { hasCompose = true; infraFiles.push(fp); }
  if (ciPatterns.some(p => p.test(fp))) { hasCI = true; infraFiles.push(fp); }
  if (k8sPatterns.some(p => p.test(fp))) { hasK8s = true; infraFiles.push(fp); }
  if (terraformPatterns.some(p => p.test(fp))) { hasTerraform = true; infraFiles.push(fp); }
  if (n.type === 'service' || n.type === 'pipeline') { infraFiles.push(fp); }
});

const deploymentTopology = {
  hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI,
  infraFiles: [...new Set(infraFiles)]
};

// I. Data Pipeline Detection
const schemaFiles = [], migrationFiles = [], dataModelFiles = [], apiHandlerFiles = [];
fileNodes.forEach(n => {
  const fp = getFilePath(n);
  if (/\.(graphql|gql|proto|prisma|sql)$/.test(fp)) schemaFiles.push(fp);
  if (/migrations?\//.test(fp) || /migration/.test(fp.toLowerCase())) migrationFiles.push(fp);
  if (/models?\.py$/.test(fp) || /models?\//.test(fp)) dataModelFiles.push(fp);
  if (/routes?\/|controllers?\/|api\/|endpoints?\//.test(fp)) apiHandlerFiles.push(fp);
});

const dataPipeline = { schemaFiles, migrationFiles, dataModelFiles, apiHandlerFiles };

// J. Documentation Coverage
const groupsWithDocs = new Set();
fileNodes.forEach(n => {
  if (n.type === 'document') {
    const fp = getFilePath(n);
    const dir = getTopDir(fp);
    groupsWithDocs.add(dir);
  }
});

const totalGroups = Object.keys(directoryGroups).length;
const undocumentedGroups = Object.keys(directoryGroups).filter(g => !groupsWithDocs.has(g));

const docCoverage = {
  groupsWithDocs: groupsWithDocs.size,
  totalGroups,
  coverageRatio: groupsWithDocs.size / totalGroups,
  undocumentedGroups
};

// K. Dependency Direction
const groupDepCounts = {};
interGroupImports.forEach(({ from, to, count }) => {
  const key = `${from}::${to}`;
  const revKey = `${to}::${from}`;
  groupDepCounts[key] = (groupDepCounts[key] || 0) + count;
});

const dependencyDirection = [];
const seen = new Set();
interGroupImports.forEach(({ from, to }) => {
  const key = `${from}::${to}`;
  const revKey = `${to}::${from}`;
  if (seen.has(key) || seen.has(revKey)) return;
  seen.add(key);
  const forward = groupDepCounts[key] || 0;
  const reverse = groupDepCounts[revKey] || 0;
  if (forward >= reverse) {
    dependencyDirection.push({ dependent: from, dependsOn: to });
  } else {
    dependencyDirection.push({ dependent: to, dependsOn: from });
  }
});

// File stats
const filesPerGroup = {};
Object.entries(directoryGroups).forEach(([g, ids]) => { filesPerGroup[g] = ids.length; });
const nodeTypeCounts = {};
Object.entries(nodeTypeGroups).forEach(([t, ids]) => { nodeTypeCounts[t] = ids.length; });

const fileStats = {
  totalFileNodes: fileNodes.length,
  filesPerGroup,
  nodeTypeCounts
};

// Top fan-in/fan-out
const fileFanIn = Object.fromEntries(
  Object.entries(fanIn).sort((a, b) => b[1] - a[1]).slice(0, 20)
);
const fileFanOut = Object.fromEntries(
  Object.entries(fanOut).sort((a, b) => b[1] - a[1]).slice(0, 20)
);

const results = {
  scriptCompleted: true,
  directoryGroups,
  nodeTypeGroups,
  crossCategoryEdges,
  interGroupImports,
  intraGroupDensity,
  patternMatches,
  deploymentTopology,
  dataPipeline,
  docCoverage,
  dependencyDirection,
  fileStats,
  fileFanIn,
  fileFanOut
};

fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
console.log('Analysis complete. Total nodes:', fileNodes.length);
process.exit(0);
