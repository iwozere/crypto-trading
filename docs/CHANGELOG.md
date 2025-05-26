# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2024-06-XX
### Added
- `/api/health` endpoint (simple health check, no auth)
- `/api/health/full` endpoint (detailed health check, requires login)
- `/api/bot-types` endpoint (returns available bot types)
- Session cookie security flags: Secure, HttpOnly, SameSite=Lax
- Version info in web GUI footer
- Custom 404 error page
- Unified logging to file via `src/notification/logger.py`
- OpenAPI spec updates for new endpoints and security

### Changed
- Improved code quality: removed dead/commented code, standardized naming
- Improved security: recommended HTTPS, rate limiting, audit logging
- Improved deployment: recommendations for Docker, CI/CD, log rotation

## [1.0.0] - 2024-05-XX
### Added
- Initial release: core trading bot management, web GUI, REST API, optimizers, notification system, backtesting, and user authentication. 