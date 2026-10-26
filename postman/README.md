# Test the API with Postman

## 1. Import the files

In Postman, click **Import** and select both files from this folder:

- `Clinic Booking API.postman_collection.json`
- `Clinic Booking API.postman_environment.json`

## 2. Select the environment

Select **Clinic Booking API — Local or Deployed** in the environment dropdown.
Set `base_url` to the API address, without a trailing slash:

- Local: `http://127.0.0.1:8000` (use the Postman desktop app or desktop agent).
- Deployed: the public application URL provided with the submission.

The default login is already filled in:

| Field | Value |
| --- | --- |
| Username | `demo_patient_001` |
| Password | `ClinicDemo-Patients-2030!` |

If you seeded with a different password, update `password` in the environment.

## 3. Run the tests

1. Open **01 - Booking walkthrough** and click **Run**.
2. Keep all 18 requests selected, in numbered order, with **1 iteration**.
3. Run the folder and review the test results.

The collection automatically logs in, saves tokens and IDs, and finds future
available slots. It tests booking, rescheduling, cancellation, and expected errors.
Some requests intentionally return `400` or `409`; their tests should still pass.
The final request cancels the test booking. Cancelled records remain as history.

Leave `test_date` empty for automatic date selection, or enter a future date in
`YYYY-MM-DD` format. Registration is optional and can be tested separately in
**02 - Optional registration**.

## Local data setup

If you are running the project locally, start the API and make sure migrations
have been applied. Run these commands from the folder containing `manage.py`:

```powershell
python manage.py seed_patients
python manage.py seed_doctors
```

You do not need to seed appointments; the walkthrough creates its own bookings.
For the deployed API, demo data should already be prepared by the developer.

If you stop a run after booking, cancel that appointment manually to release its
slot. When sharing an exported environment, clear saved tokens and private credentials.
