# Component Relationship Map

> **Project:** [Your Project Name]  
> **Last Updated:** [Date]  
> **Purpose:** Document how components interact and depend on each other

---

## Component Overview

### Component List

| ID | Component Name | Type | Primary Responsibility |
|----|---------------|------|----------------------|
| C1 | Frontend | UI Layer | User interface and interaction |
| C2 | API Gateway | Entry Point | Route requests, auth |
| C3 | Auth Service | Service | Authentication/Authorization |
| C4 | User Service | Service | User management |
| C5 | Order Service | Service | Order processing |
| C6 | Database | Data Store | Data persistence |
| C7 | Cache | Data Store | Temporary data storage |
| C8 | Message Queue | Infrastructure | Async job processing |

---

## Relationship Matrix

**Legend:**
- `D` = Direct Dependency (synchronous call)
- `A` = Async Dependency (via queue/events)
- `R` = Reads from
- `W` = Writes to
- `-` = No relationship

|     | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|-----|----|----|----|----|----|----|----|----|
| **C1** | - | D | - | - | - | - | - | - |
| **C2** | - | - | D | D | D | - | R | - |
| **C3** | - | - | - | R | - | R/W | R/W | - |
| **C4** | - | - | - | - | - | R/W | R | A |
| **C5** | - | - | - | D | - | R/W | R | A |
| **C6** | - | - | - | - | - | - | - | - |
| **C7** | - | - | - | - | - | - | - | - |
| **C8** | - | - | - | D | D | - | - | - |

---

## Component Details

### C1: Frontend

**Technology:** React, TypeScript

**Location:** `src/frontend/`

**Depends On:**
- C2 (API Gateway) - All API requests go through gateway

**Depended By:**
- None (top-level UI component)

**Interfaces:**
- REST API client (`src/api/client.ts`)
- WebSocket connection (for notifications)

**Data Flow:**
```
User Action → Component → API Call → API Gateway → Backend Services
```

**Key Files:**
- `src/App.tsx` - Main app component
- `src/api/` - API client
- `src/components/` - UI components

---

### C2: API Gateway

**Technology:** Express.js, TypeScript

**Location:** `src/gateway/`

**Depends On:**
- C3 (Auth Service) - Token validation
- C4 (User Service) - User operations
- C5 (Order Service) - Order operations
- C7 (Cache) - Response caching

**Depended By:**
- C1 (Frontend) - All client requests

**Interfaces:**
- REST API endpoints (`src/gateway/routes/`)
- Middleware (`src/gateway/middleware/`)

**Responsibilities:**
- Request routing
- Authentication middleware
- Rate limiting
- Response transformation
- Error handling

**Key Files:**
- `src/gateway/server.ts` - Entry point
- `src/gateway/routes/` - Route definitions
- `src/gateway/middleware/auth.ts` - Auth middleware

---

### C3: Auth Service

**Technology:** Node.js, JWT

**Location:** `src/services/auth/`

**Depends On:**
- C6 (Database) - User credentials, sessions
- C7 (Cache) - Token blacklist, session cache

**Depended By:**
- C2 (API Gateway) - Token validation
- C4 (User Service) - User creation triggers

**Interfaces:**
```typescript
interface AuthService {
  login(email: string, password: string): Promise<{ token: string }>;
  logout(token: string): Promise<void>;
  validateToken(token: string): Promise<User>;
  refreshToken(refreshToken: string): Promise<{ token: string }>;
}
```

**Data Models:**
- `Session` - Active user sessions
- `RefreshToken` - Long-lived tokens

**Key Files:**
- `src/services/auth/AuthService.ts`
- `src/services/auth/TokenManager.ts`

---

### C4: User Service

**Technology:** Node.js, TypeORM

**Location:** `src/services/user/`

**Depends On:**
- C6 (Database) - User data persistence
- C7 (Cache) - User profile caching
- C8 (Message Queue) - Async operations (email sending)

**Depended By:**
- C2 (API Gateway) - User endpoints
- C5 (Order Service) - User validation
- C8 (Message Queue workers) - Profile updates

**Interfaces:**
```typescript
interface UserService {
  createUser(data: CreateUserDto): Promise<User>;
  getUserById(id: string): Promise<User>;
  updateUser(id: string, data: UpdateUserDto): Promise<User>;
  deleteUser(id: string): Promise<void>;
  findUserByEmail(email: string): Promise<User | null>;
}
```

**Data Models:**
- `User` - User entity
- `UserProfile` - Extended profile data

**Key Files:**
- `src/services/user/UserService.ts`
- `src/services/user/UserRepository.ts`
- `src/services/user/models/User.ts`

---

### C5: Order Service

**Technology:** Node.js, TypeORM

**Location:** `src/services/order/`

**Depends On:**
- C4 (User Service) - Validate user exists
- C6 (Database) - Order persistence
- C7 (Cache) - Order status caching
- C8 (Message Queue) - Order notifications

**Depended By:**
- C2 (API Gateway) - Order endpoints
- C8 (Message Queue workers) - Order processing

**Interfaces:**
```typescript
interface OrderService {
  createOrder(userId: string, items: OrderItem[]): Promise<Order>;
  getOrder(orderId: string): Promise<Order>;
  updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order>;
  getUserOrders(userId: string): Promise<Order[]>;
}
```

**Data Models:**
- `Order` - Order entity
- `OrderItem` - Line items
- `Payment` - Payment records

**Key Files:**
- `src/services/order/OrderService.ts`
- `src/services/order/OrderRepository.ts`
- `src/services/order/models/Order.ts`

---

### C6: Database (PostgreSQL)

**Technology:** PostgreSQL 15

**Location:** Managed service / Docker container

**Depends On:**
- None

**Depended By:**
- C3 (Auth Service) - Credentials, sessions
- C4 (User Service) - User data
- C5 (Order Service) - Order data

**Schema Tables:**
- `users` - User accounts
- `sessions` - Active sessions
- `orders` - Order records
- `order_items` - Order line items
- `payments` - Payment transactions

**Migrations:** `migrations/`

**Connection:**
- Pool size: 20 connections
- Timeout: 30s
- Connection string: `DATABASE_URL` env var

---

### C7: Cache (Redis)

**Technology:** Redis 7

**Location:** Managed service / Docker container

**Depends On:**
- None

**Depended By:**
- C2 (API Gateway) - Response caching
- C3 (Auth Service) - Token blacklist, session cache
- C4 (User Service) - Profile caching
- C5 (Order Service) - Order status caching

**Cache Keys:**
- `session:{userId}` - User sessions (TTL: 1 hour)
- `user:{userId}` - User profiles (TTL: 15 minutes)
- `order:{orderId}` - Order data (TTL: 5 minutes)
- `api:response:{hash}` - API responses (TTL: 2 minutes)

**Operations:**
- READ: Cache hit → return
- WRITE: Update cache + database
- INVALIDATION: On data mutation

---

### C8: Message Queue (RabbitMQ)

**Technology:** RabbitMQ

**Location:** Managed service / Docker container

**Depends On:**
- C4 (User Service) - Process user events
- C5 (Order Service) - Process order events

**Depended By:**
- C4 (User Service) - Publish user events
- C5 (Order Service) - Publish order events

**Queues:**
- `user.created` - New user registrations
- `user.updated` - Profile updates
- `order.created` - New orders
- `order.paid` - Payment confirmations
- `email.send` - Email delivery

**Workers:**
- `EmailWorker` - Send transactional emails
- `NotificationWorker` - Push notifications
- `AnalyticsWorker` - Track events

---

## Interaction Patterns

### Synchronous (Request-Response)

```
Frontend → API Gateway → Service → Database → Service → API Gateway → Frontend
```

**Example:** Get User Profile
1. Frontend requests `/api/users/123`
2. API Gateway validates token (Auth Service)
3. API Gateway forwards to User Service
4. User Service checks cache
5. If miss, User Service queries database
6. User Service returns data
7. API Gateway transforms and returns to Frontend

### Asynchronous (Event-Driven)

```
Service → Message Queue → Worker → External Service
```

**Example:** User Registration
1. User Service creates user in database
2. User Service publishes `user.created` event
3. Email Worker consumes event
4. Email Worker sends welcome email (external)
5. Analytics Worker logs event

---

## Data Flow Diagrams

### User Registration Flow

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │ POST /api/users
     ▼
┌──────────────┐
│ API Gateway  │
└────┬─────────┘
     │
     ▼
┌──────────────┐     ┌──────────┐
│ User Service │────▶│ Database │ (Write)
└────┬─────────┘     └──────────┘
     │
     ▼
┌──────────────┐
│ Message Queue│
└────┬─────────┘
     │
     ▼
┌──────────────┐
│ Email Worker │
└──────────────┘
```

### Order Placement Flow

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │ POST /api/orders
     ▼
┌──────────────┐
│ API Gateway  │
└────┬─────────┘
     │
     ▼
┌──────────────┐
│ Order Service│
└────┬────┬────┘
     │    │
     │    └──────▶ User Service (validate user)
     │
     ▼
┌──────────┐     ┌─────────┐
│ Database │◀───▶│  Cache  │
└──────────┘     └─────────┘
     │
     ▼
┌──────────────┐
│ Message Queue│
└────┬─────────┘
     │
     ├─▶ Payment Worker
     ├─▶ Inventory Worker
     └─▶ Notification Worker
```

---

## Dependency Graph

### Visual Representation

```
                    ┌──────────────┐
                    │   Frontend   │
                    │     (C1)     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ API Gateway  │
                    │     (C2)     │
                    └──┬───┬───┬───┘
                       │   │   │
         ┌─────────────┘   │   └─────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │  Auth   │      │  User   │      │  Order  │
    │ Service │      │ Service │      │ Service │
    │  (C3)   │      │  (C4)   │◀─────│  (C5)   │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │
         │                └────────┬───────┘
         │                         │
         ▼                         ▼
    ┌─────────────────────────────────┐
    │         Database (C6)            │
    └─────────────────────────────────┘
         ▲                         ▲
         │                         │
    ┌────┴────┐               ┌────┴────┐
    │  Cache  │               │  Queue  │
    │  (C7)   │               │  (C8)   │
    └─────────┘               └─────────┘
```

### Dependency Layers

**Layer 1 (UI):**
- Frontend (C1)

**Layer 2 (Gateway):**
- API Gateway (C2)

**Layer 3 (Services):**
- Auth Service (C3)
- User Service (C4)
- Order Service (C5)

**Layer 4 (Data/Infrastructure):**
- Database (C6)
- Cache (C7)
- Message Queue (C8)

---

## Communication Protocols

| From | To | Protocol | Format | Auth |
|------|-----|----------|--------|------|
| Frontend | API Gateway | HTTPS | JSON | JWT |
| API Gateway | Services | HTTP | JSON | Internal |
| Services | Database | TCP | SQL | Credentials |
| Services | Cache | TCP | Redis Protocol | Password |
| Services | Queue | AMQP | JSON | Credentials |

---

## Error Propagation

### Frontend ← API Gateway
- HTTP status codes
- Standardized error format:
```json
{
  "error": "ResourceNotFound",
  "message": "User not found",
  "code": 404
}
```

### API Gateway ← Services
- Throw exceptions
- Services return standardized errors
- Gateway transforms to HTTP responses

### Services ← Database/Cache
- Connection errors → Retry logic
- Query errors → Log and rethrow
- Data errors → Validation error

---

## Circular Dependencies

**Status:** ✅ None detected

**Prevention Measures:**
- One-way dependencies enforced
- Services communicate via gateway
- Event-driven async communication
- Dependency injection

---

## Testing Strategy

### Unit Tests
- Each component tested in isolation
- Mock dependencies
- Focus: Business logic

### Integration Tests
- Test component interactions
- Real database (test instance)
- Focus: Data flows

### E2E Tests
- Test complete user flows
- All components running
- Focus: User scenarios

---

## Monitoring Points

| Component | Metrics | Alerts |
|-----------|---------|--------|
| API Gateway | Request rate, latency, errors | Error rate > 5% |
| Services | Method latency, errors | Latency > 1s |
| Database | Connection pool, query time | Pool exhaustion |
| Cache | Hit rate, memory usage | Hit rate < 70% |
| Queue | Message backlog, processing time | Backlog > 1000 |

---

## Scaling Considerations

### Horizontal Scaling
- ✅ Frontend (static files → CDN)
- ✅ API Gateway (stateless)
- ✅ Auth Service (stateless with Redis)
- ✅ User Service (stateless)
- ✅ Order Service (stateless)

### Vertical Scaling
- Database (primary bottleneck)
- Cache (memory-bound)

### Future Improvements
- [ ] Database read replicas
- [ ] Service mesh for inter-service communication
- [ ] API Gateway clustering
- [ ] Distributed tracing

---

## Notes & Gotchas

> [!IMPORTANT]
> Critical information for developers

- **Service Discovery:** Currently hardcoded URLs, plan to use service registry
- **Circuit Breaker:** Not implemented yet, services fail fast
- **Database Transactions:** Only within single service, no distributed transactions
- **Event Ordering:** Queue does not guarantee ordering across partitions

---

## Change Log

| Date | Author | Change |
|------|--------|---------|
| 2024-01-15 | John Doe | Initial component map |
|  |  |  |
