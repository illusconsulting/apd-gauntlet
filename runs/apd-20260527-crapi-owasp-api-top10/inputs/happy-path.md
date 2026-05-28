# crAPI — Happy Path

The "happy path" is the workflow the application is designed to support
when used as intended. This document describes the legitimate user
journey so reviewers can distinguish expected behaviour from the
intentional vulnerabilities catalogued in `threat-model.md`.

## Prerequisites

- crAPI is running locally via Docker Compose, Helm, or Vagrant.
- The deployer can reach:
  - the SPA at `http://localhost:8888`
  - the Mailhog UI at `http://localhost:8025` (for inspecting OTPs)
  - optionally, the OpenAPI spec at
    `http://localhost:8888/workshop/openapi-spec/`

## Conceptual model

crAPI is a backend for:

- User identity and authentication.
- User profiles, including profile videos and a vehicle list.
- Mechanic discovery and service-request submission.
- A small marketplace (orders, returns, coupons, stored balance).
- A community area (blog posts, comments).
- A chatbot assistant grounded against the OpenAPI spec.

The happy path is how a single legitimate user creates an account,
adds a vehicle, contacts a mechanic, places an order, and posts to
the community.

## Step-by-step

### 1. User registration

- **Endpoint:** `POST /identity/api/auth/signup`
- **Request:** email, name, phone, password.
- **Expected result:** the account is created in the identity-service
  Postgres database. A signup-confirmation email is dispatched to
  Mailhog (`http://localhost:8025`). For Mailhog-routed addresses
  (default: `*@example.com`), the email is observable in the Mailhog
  inbox.

### 2. User login

- **Endpoint:** `POST /identity/api/auth/login`
- **Request:** email + password.
- **Expected result:** a bearer JWT is returned. Default token TTL is
  the value of `JWT_EXPIRATION` (604800000 ms, 7 days).

This bearer token is the authentication material for every subsequent
authenticated call. Include it as `Authorization: Bearer <token>`.

### 3. Access the user profile

- **Endpoint:** `GET /identity/api/v2/user/dashboard`
- **Request:** bearer token only.
- **Expected result:** dashboard payload — user's own profile data,
  recent activity, vehicle list.

### 4. Add a vehicle

- **Endpoint:** `POST /identity/api/v2/vehicle/add_vehicle`
- **Request:** VIN, pincode. The pincode is delivered by email after
  signup (or by re-initiating from the dashboard's "Resend Email"
  control, which hits `POST /identity/api/v2/vehicle/resend_email`).
- **Expected result:** the vehicle is added to the user's account
  and appears in `GET /identity/api/v2/vehicle/vehicles`. The
  dashboard now shows the vehicle with its model, year, and last
  known location.

### 5. Refresh the vehicle's location

- **Endpoint:** `GET /identity/api/v2/vehicle/{vehicleId}/location`
- **Request:** bearer token; the `vehicleId` from step 4.
- **Expected result:** latest latitude / longitude for the vehicle.

### 6. Contact a mechanic

- **Endpoint:** `POST /workshop/api/merchant/contact_mechanic`
- **Request:** vehicle ID, problem description, target mechanic, and
  a webhook URL (`mechanic_api`) that the workshop calls to deliver
  the service request.
- **Expected result:** a service request is created in the workshop
  Postgres database; a `report_link` is returned in the response,
  pointing at the mechanic-report resource. The mechanic later
  posts a report via `POST /workshop/api/mechanic/receive_report`.

### 7. Browse and order from the shop

- **Endpoints:** `GET /workshop/api/shop/products`,
  `POST /workshop/api/shop/orders`.
- **Request:** product ID + quantity.
- **Expected result:** the account's `credit` balance is decremented
  by `unit_price × quantity`. The order appears in
  `GET /workshop/api/shop/orders` and is retrievable individually at
  `GET /workshop/api/shop/orders/{order_id}`.

### 8. Apply a coupon (optional)

- **Endpoints:** `POST /community/api/v2/coupon/validate-coupon` then
  `POST /workshop/api/shop/apply_coupon`.
- **Request:** coupon code.
- **Expected result:** the coupon is recognised by the community
  service (Mongo lookup), and the workshop service marks it as
  applied for the calling user (Postgres update), adjusting the
  user's stored balance.

### 9. Return an order

- **Endpoints:** `POST /workshop/api/shop/orders/return_order`,
  `GET /workshop/api/shop/return_qr_code`.
- **Request:** order ID.
- **Expected result:** a return QR code is generated, the order
  status moves to `RETURNED`, and the user's balance is credited.

### 10. Post to the community

- **Endpoints:** `POST /community/api/v2/community/posts`,
  `POST /community/api/v2/community/posts/{postId}/comment`.
- **Request:** post title + body (or comment body).
- **Expected result:** the post / comment is stored in Mongo and
  appears in `GET /community/api/v2/community/posts/recent` for all
  users.

### 11. Upload a profile video (optional)

- **Endpoints:** `POST /identity/api/v2/user/videos`,
  `GET /identity/api/v2/user/videos/{video_id}`.
- **Request:** video metadata + binary.
- **Expected result:** the video is stored against the user and
  retrievable via the GET endpoint.

### 12. Talk to the chatbot (optional)

- **Endpoint:** `POST /chatbot/genai/chat`.
- **Request:** natural-language prompt.
- **Expected result:** the chatbot's RAG layer retrieves relevant
  passages from the embedded OpenAPI spec, the configured LLM
  generates a response, and the chatbot returns it. For
  OpenAI / Anthropic configurations, the operator must first call
  `POST /chatbot/genai/init` to supply an API key for the session.

## Normal application usage

Past step 12, a user continues to:

- Create or view resources they own.
- Receive HTTP 2xx on permitted actions and HTTP 4xx on disallowed
  ones.
- See their own dashboard reflect their actions in near-real-time.

At this point the system's baseline behaviour is understood; any
deviation observable in subsequent exploration is a candidate
finding.

## Next steps

Once the happy path is known, reviewers proceed to:

- `threat-model.md` — the STRIDE-organised view of where crAPI
  intentionally deviates from this baseline.
- `docs/challenges.md` / `docs/challengeSolutions.md` (in the
  upstream repo) — the per-challenge exploit walk-throughs.
