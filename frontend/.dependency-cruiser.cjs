/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment:
        'Circular dependencies make code hard to understand and maintain',
      from: {},
      to: {
        circular: true,
      },
    },
    {
      name: 'no-orphans',
      severity: 'warn',
      comment:
        "Orphan modules (not imported by anything) may indicate dead code",
      from: {
        orphan: true,
        pathNot: [
          '^src/main\\.ts$',
          '\\.(spec|test|stories)\\.(ts|js|vue)$',
          '^src/vite-env\\.d\\.ts$',
        ],
      },
      to: {},
    },
    {
      name: 'no-views-to-services',
      severity: 'error',
      comment:
        'Views should not call API services directly; use stores instead',
      from: {
        path: '^src/views',
      },
      to: {
        path: '^src/services',
      },
    },
    {
      name: 'no-components-to-services',
      severity: 'error',
      comment:
        'Components should not call API services directly; use stores instead',
      from: {
        path: '^src/components',
      },
      to: {
        path: '^src/services',
      },
    },
    {
      name: 'no-components-to-stores',
      severity: 'warn',
      comment:
        'Consider whether components should access stores directly or receive props from parent views',
      from: {
        path: '^src/components',
        pathNot: '^src/components/layout',
      },
      to: {
        path: '^src/stores',
      },
    },
    {
      name: 'no-services-to-stores',
      severity: 'error',
      comment:
        'Services should not depend on stores; stores call services, not the other way around',
      from: {
        path: '^src/services',
      },
      to: {
        path: '^src/stores',
      },
    },
    {
      name: 'no-services-to-views',
      severity: 'error',
      comment:
        'Services should not import from views',
      from: {
        path: '^src/services',
      },
      to: {
        path: '^src/views',
      },
    },
    {
      name: 'no-services-to-components',
      severity: 'error',
      comment:
        'Services should not import from components',
      from: {
        path: '^src/services',
      },
      to: {
        path: '^src/components',
      },
    },
  ],
  options: {
    doNotFollow: {
      path: 'node_modules',
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: 'tsconfig.json',
    },
    enhancedResolveOptions: {
      exportsFields: ['exports'],
      conditionNames: ['import', 'require', 'node', 'default'],
    },
    reporterOptions: {
      dot: {
        collapsePattern: 'node_modules/[^/]+',
      },
      archi: {
        collapsePattern: '^(node_modules|src/types|src/router)/[^/]+',
      },
      text: {
        highlightFocused: true,
      },
    },
  },
};
