from django.test import SimpleTestCase
from rest_framework.test import APIClient


class APIDocumentationTests(SimpleTestCase):
    """Schema generation must work anonymously without database access."""

    def setUp(self):
        self.client = APIClient()

    def schema(self):
        response = self.client.get("/swagger.json")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_all_endpoints_are_documented_without_database_queries(self):
        schema = self.schema()
        self.assertEqual(schema["swagger"], "2.0")
        self.assertEqual(set(schema["paths"]), {
            "/auth/register", "/auth/login", "/auth/token/refresh",
            "/doctors", "/doctors/{id}/availability", "/appointments",
            "/appointments/{id}/cancel", "/appointments/{id}/reschedule",
            "/patients/{patient_id}/appointments",
        })
        self.assertNotIn("status", schema)

    def test_ui_and_raw_formats_are_accessible(self):
        for url in ("/swagger/", "/redoc/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response["Content-Type"])
        response = self.client.get("/swagger.yaml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"swagger:", response.content)

    def test_bearer_auth_and_public_operations(self):
        schema = self.schema()
        bearer = schema["securityDefinitions"]["Bearer"]
        self.assertEqual(bearer["name"], "Authorization")
        self.assertEqual(bearer["in"], "header")
        self.assertEqual(schema["paths"]["/appointments"]["post"]["security"], [{"Bearer": []}])
        self.assertEqual(schema["paths"]["/auth/login"]["post"]["security"], [])
        self.assertEqual(schema["paths"]["/doctors"]["get"]["security"], [])

    def test_availability_date_query_is_required(self):
        operation = self.schema()["paths"]["/doctors/{id}/availability"]["get"]
        parameter = next(item for item in operation["parameters"] if item["name"] == "date")
        self.assertEqual(parameter["in"], "query")
        self.assertTrue(parameter["required"])
        self.assertEqual(parameter["format"], "date")
        self.assertIn("YYYY-MM-DD", parameter["description"])
        self.assertIn("2030-01-07", parameter["description"])

    def test_booking_and_rescheduling_fields_show_datetime_examples(self):
        definitions = self.schema()["definitions"]
        for name in ("Booking", "Reschedule"):
            field = definitions[name]["properties"]["starts_at"]
            self.assertIn("YYYY-MM-DDTHH:MM:SS", field["description"])
            self.assertEqual(field["example"], "2030-01-07T10:30:00+03:00")

    def test_slots_and_appointments_document_read_only_display_time(self):
        definitions = self.schema()["definitions"]
        for name in ("Slot", "Appointment"):
            field = definitions[name]["properties"]["display_time"]
            self.assertEqual(field["type"], "string")
            self.assertTrue(field["readOnly"])
            self.assertEqual(field["example"], "6:00 PM – 6:30 PM EAT")

    def test_booking_envelope_and_single_string_errors(self):
        schema = self.schema()
        responses = schema["paths"]["/appointments"]["post"]["responses"]
        success = responses["201"]["schema"]["properties"]
        self.assertEqual(success["status"]["type"], "integer")
        self.assertEqual(success["status"]["enum"], [201])
        self.assertEqual(success["data"]["$ref"], "#/definitions/Appointment")
        self.assertNotIn("error", success)
        failure = responses["409"]["schema"]["properties"]
        self.assertEqual(failure["error"]["type"], "string")
        self.assertEqual(failure["status"]["enum"], [409])
        self.assertTrue(failure["data"]["x-nullable"])

    def test_list_pagination_and_token_payload_match_runtime(self):
        schema = self.schema()
        properties = schema["paths"]["/doctors"]["get"]["responses"]["200"]["schema"]["properties"]
        self.assertEqual(
            set(properties["data"]["properties"]), {"count", "next", "previous", "results"},
        )
        tokens = schema["paths"]["/auth/login"]["post"]["responses"]
        self.assertIn("200", tokens)
        self.assertNotIn("201", tokens)
        self.assertEqual(
            tokens["200"]["schema"]["properties"]["data"]["$ref"],
            "#/definitions/TokenPairResponse",
        )
        self.assertEqual(
            set(schema["definitions"]["TokenPairResponse"]["properties"]), {"access", "refresh"},
        )
