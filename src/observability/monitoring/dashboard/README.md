# ACGS-2 Monitoring Dashboard

**Constitutional Hash**: `cdd01ef066bc6cf2`

A React-based unified monitoring dashboard for the ACGS-2 Constitutional AI Governance System.

## Features

- **Real-time Health Monitoring**: Live service health status with WebSocket updates
- **System Metrics**: CPU, memory, disk usage with historical charts
- **Performance Analytics**: P99 latency, throughput, cache hit rate
- **Alert Management**: Severity-based alert display and filtering
- **Service Grid**: Visual grid of all monitored services
- **Constitutional Compliance**: 100% constitutional hash validation

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
monitoring/dashboard/
├── src/
│   ├── components/     # React components
│   │   ├── Dashboard.tsx       # Main dashboard
│   │   ├── HealthPanel.tsx     # Health overview
│   │   ├── MetricsChart.tsx    # Metrics visualization
│   │   ├── AlertsList.tsx      # Alerts display
│   │   ├── ServiceGrid.tsx     # Service status grid
│   │   ├── StatusBadge.tsx     # Status indicator
│   │   └── MetricCard.tsx      # Metric display card
│   ├── hooks/          # React hooks
│   │   └── useDashboard.ts     # Data fetching hooks
│   ├── types/          # TypeScript types
│   │   └── api.ts              # API response types
│   ├── utils/          # Utility functions
│   │   └── api.ts              # API client
│   ├── App.tsx         # App component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.js
```

## Components

| Component | Description |
|-----------|-------------|
| `Dashboard` | Main dashboard layout with all panels |
| `HealthPanel` | System health score and service counts |
| `MetricsChart` | CPU/Memory/Disk usage charts (Recharts) |
| `AlertsList` | Active alerts with severity filtering |
| `ServiceGrid` | Grid view of service health status |
| `StatusBadge` | Colored status indicator badge |
| `MetricCard` | Individual metric display card |

## API Integration

The dashboard connects to the Dashboard API at `http://localhost:8090`:

- `GET /dashboard/overview` - System overview
- `GET /dashboard/health` - Health status
- `GET /dashboard/metrics` - System metrics
- `GET /dashboard/alerts` - Active alerts
- `GET /dashboard/services` - Service list
- `WS /dashboard/ws` - Real-time updates

## Configuration

Set environment variables in `.env`:

```env
VITE_API_URL=http://localhost:8090
VITE_WS_URL=ws://localhost:8090
```

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Recharts** - Charts
- **Lucide React** - Icons

## License

Apache-2.0
