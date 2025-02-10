# UMBRELLA-AI Alert System Documentation

## Overview
This document describes the automated alert system for UMBRELLA-AI, including alert configurations, thresholds, and notification channels.

## Alert Categories

### 1. Test Failures
- **Severity**: Critical
- **Channels**: Slack (#critical-alerts), Email
- **Conditions**:
  - Any test failure in CI/CD pipeline
  - Failed health checks in production
  - Integration test failures

### 2. Performance Degradation
- **Severity**: Warning/Critical
- **Channels**: Slack (#monitoring, #warnings)
- **Thresholds**:
  - High Latency: 95th percentile > 2s (Warning)
  - Error Rate: > 10% in 5m (Critical)
  - Memory Usage: > 1GB (Warning)
  - Request Rate: > 100 req/s (Warning)

### 3. Service Health
- **Severity**: Critical
- **Channels**: Slack (#critical-alerts), Email
- **Conditions**:
  - Service down for > 1m
  - Dependency failures
  - Database connection issues

## Alert Configuration

### Notification Channels

1. **Slack Channels**:
   - #monitoring: General monitoring alerts
   - #critical-alerts: High-priority issues
   - #warnings: Non-critical warnings

2. **Email Notifications**:
   - Recipients: oncall@umbrella-ai.com
   - Used for: Critical alerts only
   - Format: HTML with detailed alert information

### Alert Grouping
- Grouped by: alertname, service
- Group wait: 30s
- Group interval: 5m
- Repeat interval: 4h

### Rate Limiting
- Minimum alert interval: 30s
- Resolve timeout: 5m
- Duplicate suppression: Enabled

## Testing Alert System

### Manual Testing
1. Trigger test alert:
```bash
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "service": "test",
    "severity": "critical"
  },
  "annotations": {
    "description": "This is a test alert"
  }
}]'
```

2. Verify alert reception:
   - Check Slack channels
   - Check email inbox
   - Verify Alertmanager UI

### Automated Testing
Run the test suite:
```bash
pytest tests/test_alerts.py -v
```

## Alert Response Procedures

1. **Critical Alerts**:
   - Immediate response required (SLA: 15 minutes)
   - Page on-call engineer
   - Start incident management process

2. **Warning Alerts**:
   - Response during business hours
   - Create ticket for investigation
   - Monitor for escalation

3. **Resolution**:
   - Document root cause
   - Update runbooks if needed
   - Review alert thresholds

## Maintenance

### Regular Tasks
1. Review alert thresholds monthly
2. Update contact information
3. Test notification channels
4. Clean up resolved alerts

### Configuration Updates
1. Update alertmanager.yml for channel changes
2. Modify alert rules in prometheus/rules/
3. Update alert templates as needed 