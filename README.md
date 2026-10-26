# Clinic Booking API

Savannah Informatics Implementation Engineer Assessment.

A Django REST Framework API for checking doctors' availability and booking,
cancelling, and rescheduling 30-minute appointments.

**Public application URL:** https://clinic-booking-backend-fkp7.onrender.com
**API documentation:** append `/swagger/` to the application URL.
**Postman:** [import and run instructions](postman/README.md).

## Try the live API

The deployment build prepares demo patient accounts, doctors, working hours,
and sample appointments for quick testing. Reviewers can also create their own patient
accounts through `POST /auth/register`. Doctors and working-hour schedules can
be added through [Django admin](https://clinic-booking-backend-fkp7.onrender.com/admin/)
using an authorized staff account, since these do not have creation API endpoints.

1. Open [live Swagger](https://clinic-booking-backend-fkp7.onrender.com/swagger/).
2. Use `POST /auth/login` with username `demo_patient_001` and password
   `ClinicDemo-Patients-2030!`.
3. Copy `data.access`, click **Authorize**, and enter `Bearer <access-token>`.
4. List doctors, check availability for a future weekday, and copy a returned
   `starts_at` value to book. You can then reschedule or cancel the booking.

Other demo usernames are `demo_patient_002` through `demo_patient_010`, using
that same password. The full patient list is below under **Seeded patient credentials**.
Sample appointments can become past appointments over time; choose a future
available slot when testing.

For Postman, import the files linked above and set `base_url` to
`https://clinic-booking-backend-fkp7.onrender.com`.

## 1. System design

The initial design was documented before booking implementation. Project
scaffolding and the abstract base model already existed at that stage.

### Structure and models

Generic views handle individual API operations. Serializers validate input,
services hold reusable business logic, and PostgreSQL stores the data.

| App | Models and responsibility |
| --- | --- |
| `accounts` | Custom `User` for login; `Patient` linked one-to-one to a user |
| `doctors` | `Doctor` with names, specialization, active status, and optional user account; `WorkingHour` with doctor, weekday, opening and closing times |
| `appointments` | `Appointment` linked to a patient and doctor, with start time, booking status, cancellation reason, and cancellation timestamp |
| `shared` | Abstract `BaseModel`: UUID primary key, creation and update timestamps |
| `config` | Development, production, and test settings; project URLs and server entrypoints |

A doctor has many working periods and appointments. A patient has many
appointments. Doctors do not need login accounts; staff manage their records and
working hours through Django admin. Appointment end time is calculated from the
start time rather than stored separately.

### Booking rules

- Working hours repeat weekly, with one working period per doctor per weekday.
- Slots last 30 minutes and start at `:00` or `:30`, with zero seconds.
- A booking must fit within working hours and start at least one hour from now.
- Available slots are calculated from working hours, excluding booked slots.
- Patients can access and change only their own appointments.
- Cancellation requires a reason and releases the slot. Repeated cancellation fails.
- Rescheduling keeps the same doctor and appointment ID. Invalid moves leave the
  original booking intact. Cancelled or already-started appointments cannot move.

Times use `Africa/Nairobi` (EAT, UTC+03:00). Inputs must include an offset or `Z`;
timestamps are stored in UTC. Responses also include `display_time`, for example
`6:00 PM – 6:30 PM EAT`, for easier manual testing. Book using `starts_at`.

### Preventing double booking

Booking, cancellation, and rescheduling use `transaction.atomic()`. They lock the
doctor with `select_for_update()` before checking or changing a booking.
Concurrent requests for that doctor wait and then check the latest data.

A conditional database unique constraint also prevents two `BOOKED` appointments
for the same doctor and start time. Cancelled records do not block the slot.
Slot conflicts return `409`; failed writes roll back.

### Decisions and trade-offs

- PostgreSQL provides the row locking used by the booking services. SQLite is an
  optional local fallback, but cannot verify the same concurrency behavior.
- Locking a whole doctor is simple and appropriate for five doctors, but also
  serializes writes to different slots for that doctor.
- Calculating slots avoids maintaining a separate slot table. Fixed duration
  and alignment keep overlap prevention straightforward.
- JWT authentication establishes patient ownership. Registration and login are
  supporting design choices, rather than assessment-mandated endpoints.
- Holidays, split/overnight shifts, doctor-facing accounts, and patient overlaps
  across different doctors are outside the initial scope.

## 2. Run and test the API locally

### Step 1: Install dependencies

Use Python 3.12. Clone the repository and enter the folder containing
`manage.py` and `requirements.txt`:

~~~powershell
git clone https://github.com/mutungapeter/clinic_booking.git
cd clinic_booking
~~~

Create and activate a virtual environment, then install dependencies:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

### Step 2: Choose the local database

**SQLite is the default.** No database installation or PostgreSQL configuration
is needed for a quick local setup. Django creates `db.sqlite3` in the project
root when you run migrations in Step 3.

Use development settings and ensure this terminal is not pointing to the hosted
database through a previously configured `POSTGRES_DB`:

~~~powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
Remove-Item Env:POSTGRES_DB -ErrorAction SilentlyContinue
~~~

Then continue to Step 3. Steps 3 and 4 seed your local database and start the
server at `http://127.0.0.1:8000/`.

**Optional: PostgreSQL locally.** To use PostgreSQL instead, create an empty
local database and set its connection details in the same PowerShell terminal:

~~~powershell
$env:POSTGRES_DB = "clinic_booking"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "your-local-password"
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_SSLMODE = "disable"
Remove-Item Env:POSTGRES_CHANNEL_BINDING -ErrorAction SilentlyContinue
~~~

Setting a nonempty `POSTGRES_DB` switches Django from SQLite to PostgreSQL.
Production requires PostgreSQL. Use PostgreSQL to verify concurrent booking
protection; SQLite is sufficient for exploring the API locally.

The application does **not** automatically load `.env` files. Set variables in
the terminal as shown above; see [.env.example](.env.example) for configuration
names.

### Step 3: Apply migrations and seed demo data

These commands are for a new local database. Hosted demo data is prepared by
the Render build after migrations.

~~~powershell
python manage.py check
python manage.py migrate
python manage.py seed_patients
python manage.py seed_doctors
python manage.py seed_appointments
~~~

| Command | Demo data |
| --- | --- |
| `seed_patients` | Ten patient accounts and profiles |
| `seed_doctors` | Five doctors with specializations and Monday-Friday working hours, 09:00-17:00 |
| `seed_appointments` | Ten future bookings within a 14-day window, starting tomorrow |

Commands are safe to rerun: existing passwords and schedules are preserved;
existing active demo bookings count toward the requested appointment target.
Blank specializations on seeded doctors are filled without replacing nonblank
values. Appointment seeding uses the normal booking service.

To create more demo bookings, use `python manage.py seed_appointments --count 20 --days 30`.
Appointment seeding is optional for Postman: the walkthrough creates its own bookings.

### Seeded patient credentials

**Default password for every account below: `ClinicDemo-Patients-2030!`**

| Patient | Login username |
| --- | --- |
| Amina Otieno | `demo_patient_001` |
| Brian Kamau | `demo_patient_002` |
| Carol Wanjiku | `demo_patient_003` |
| David Omondi | `demo_patient_004` |
| Esther Njeri | `demo_patient_005` |
| Felix Mutua | `demo_patient_006` |
| Grace Achieng | `demo_patient_007` |
| Henry Kiptoo | `demo_patient_008` |
| Irene Wambui | `demo_patient_009` |
| James Mwangi | `demo_patient_010` |

If `--password` or `SEED_PATIENT_PASSWORD` was provided when seeding, use that
password instead. Rerunning seeds does not reset existing passwords.
Doctors have no seeded login accounts.

### Optional: Local admin access

Admin access is not required to test the assessment endpoints. To manage doctors
and working hours in your local database, run after migrations:

~~~powershell
python manage.py createsuperuser
~~~

Follow the prompts, start the server, and log in at
[local Django admin](http://127.0.0.1:8000/admin/).

### Step 4: Start the server and log in

~~~powershell
python manage.py runserver
~~~

Open [Swagger](http://127.0.0.1:8000/swagger/), [ReDoc](http://127.0.0.1:8000/redoc/),
or [Django admin](http://127.0.0.1:8000/admin/).

Send `POST /auth/login`:

~~~json
{
  "username": "demo_patient_001",
  "password": "ClinicDemo-Patients-2030!"
}
~~~

Copy `data.access`. In Swagger, click **Authorize** and enter
`Bearer <access-token>`. Access and refresh tokens currently last one day.
Exchange `{"refresh": "<refresh-token>"}` at `POST /auth/token/refresh` for another
access token, or log in again when the refresh token expires.

### Step 5: Try the booking flow

1. List doctors and copy a doctor ID.
2. Request that doctor's availability for a future date using `YYYY-MM-DD`.
3. Book using `doctor_id` and a `starts_at` copied from the returned slots.
4. Try booking the same slot again: expect `409`.
5. Reschedule using another available `starts_at`; check that the old slot is free.
6. Cancel with a `reason`; check that the slot is free. Repeating cancellation returns `409`.

For automated manual checks, import the [Postman collection](postman/Clinic%20Booking%20API.postman_collection.json)
and [environment](postman/Clinic%20Booking%20API.postman_environment.json).
Select the environment, set `base_url`, and run **01 - Booking walkthrough** in
numbered order. It saves tokens/IDs, chooses future slots, and checks expected errors.

### Endpoints

Paths do not use trailing slashes. Doctor listing and availability are public;
booking changes and patient appointment lists require authentication.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/appointments` | Book a slot |
| GET | `/doctors/{id}/availability?date=YYYY-MM-DD` | Available 30-minute slots |
| PATCH | `/appointments/{id}/cancel` | Cancel with a reason |
| PATCH | `/appointments/{id}/reschedule` | Move to another slot |
| GET | `/patients/{id}/appointments` | Bonus: upcoming appointments, sorted by date |
| GET | `/doctors` | List active doctors and specializations |
| POST | `/auth/register` | Create a patient account |
| POST | `/auth/login` | Obtain access and refresh tokens |
| POST | `/auth/token/refresh` | Refresh the access token |

Successful responses contain numeric `status`, `message`, and `data`. Successful
fetches use a null message. Failures use null message/data and one `error` string.
HTTP codes include `201` for booking, `400` for validation, `401` for authentication,
`403` for accounts without a patient profile, `404` for missing/inaccessible
resources, and `409` for booking/state conflicts. Lists are paginated.

### Step 6: Run the tests

From the directory containing `manage.py`:

~~~powershell
python manage.py test --settings=config.settings.testing --noinput
~~~

With PostgreSQL configured, the suite includes simultaneous booking and
cancellation/rescheduling tests. The database user needs permission to create a
separate test database, which Django removes afterward. Use a development/test
server. Without PostgreSQL, SQLite functional tests run and concurrency tests skip.

The last full PostgreSQL verification passed **69 tests**, including both
concurrency tests. Coverage includes booking validation, slot release, failed
rescheduling rollback, permissions, tokens, seeds, and API documentation.

## 3. Deployment and CI/CD

**Provider:** Render (native Python), with Neon PostgreSQL. **Deployment branch:** `main`.
The hosted API is available at https://clinic-booking-backend-fkp7.onrender.com.

[GitHub Actions](.github/workflows/ci.yml) runs Django checks, migration
consistency checks, and all tests on PostgreSQL 17 for every pull request.
After a merge pushes code to `main`, it reruns verification, deploys the tested
commit to Render, waits until that deployment is live, and checks the public
`/swagger.json` endpoint. Failed deployments fail the workflow.
Protect `main` to require PRs and passing tests; direct pushes otherwise also deploy.

Create a Render **Web Service** linked to this repository and branch `main`.
Use the repository-root [render.yaml](render.yaml) Blueprint, or configure:

| Setting | Value |
| --- | --- |
| Language/runtime | Python 3; the root `.python-version` selects Python 3.12 |
| Root directory | Leave empty (repository root) |
| Build command | `bash build.sh` |
| Start command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --access-logfile - --error-logfile -` |
| Health check | `/swagger.json` |
| Auto-deploy | Off; GitHub Actions triggers deployment after tests pass |

The Blueprint uses Render's free web-service plan and an external Neon database.
Set the following GitHub Actions values:

| Type | Name |
| --- | --- |
| Secret | `RENDER_API_KEY` — create in Render account settings under API Keys |
| Variable | `RENDER_SERVICE_ID` — the web service's `srv-...` ID |
| Variable | `RENDER_PUBLIC_URL` — actual HTTPS service URL, such as `https://your-service.onrender.com` |

In the Render service's **Environment** tab, configure the values in
[.env.example](.env.example). Use the actual service hostname for
`DJANGO_ALLOWED_HOSTS`, its full HTTPS origin for `DJANGO_CSRF_TRUSTED_ORIGINS`,
a generated `DJANGO_SECRET_KEY`, and the actual Neon `POSTGRES_*` credentials.
Use `POSTGRES_SSLMODE=require` and `POSTGRES_CHANNEL_BINDING=require` for Neon.
A `DATABASE_URL` alone is not read. The Blueprint generates a Django secret key.
For fully automatic deployment, do not require manual approval on GitHub's
`production` environment.

Docker is not required by the assessment or this hosting setup. Render's native
Python runtime runs [build.sh](build.sh) to install dependencies, collect
static files, apply migrations, and seed demo data. Gunicorn serves the API; WhiteNoise serves
Swagger/admin assets. CI still uses a disposable PostgreSQL container for tests.

The first service creation needs an initial Render deployment. After that,
GitHub Actions deploys the exact tested commit through the Render API. Keep
independent auto-deploys off so they do not bypass the test gate. Configure the
live Neon `POSTGRES_*` variables in Render. After migrations, every build runs
`seed_patients`, `seed_doctors`, and `seed_appointments` in that order against
the configured database. Existing accounts, passwords, and schedules are
preserved; appointment seeding fills a target of ten future demo bookings.
A seed command failure stops the build. No Render Shell access is required.

The application is deployed. After deploying this build configuration, confirm
the seed command output in Render logs and test a demo login. Verify the pull
request test run and deployment after merging before submission.
See [Render's Django guide](https://render.com/docs/deploy-django)
and [deployment API](https://api-docs.render.com/reference/create-deploy).

## 4. AI reflection

### What did I use AI for?

After creating the initial folders and apps, I used AI to help bootstrap the
project and implement the API. I reviewed the generated code against my coding
standards and structure, and made corrections to naming and model relationships.

I also used AI to discuss design choices, draft documentation, generate tests
for booking and error cases, prepare seed commands, add Swagger/Postman support,
and prepare the CI/CD and Render configuration. The application is now hosted
on Render, with demo seeding included in the build for manual testing.

### One suggestion that improved the work

My prompt, paraphrased, was: "Use separate DRF generic views for each API operation
and reusable services where needed."

AI helped implement that structure with booking validation shared between
creation and rescheduling. This kept the views focused and avoided maintaining
two separate versions of the booking rules.

### One example of wrong or incomplete output

AI reused some of my services incorrectly and initially used DRF's default
`detail` error response instead of my agreed response structure. I reviewed and
corrected the service calls and response handling to follow my project conventions:
numeric `status`, `message`, and `data`, with a single `error` string for failures.
These corrections reinforced the need to review generated code against the
existing service design and API response contract.

### Two decisions I made without AI

1. **Django and Django REST Framework:** I selected this stack before asking AI to
   bootstrap the implementation. It matched the backend stack I wanted to use.
2. **Separate generic views for individual operations:** I specified this approach
   as part of my coding standards. It makes each endpoint's responsibility clear
   and the resulting code easier for me to review and maintain.
