from fastapi import FastAPI, File, UploadFile, HTTPException
from groq import Groq
from dotenv import load_dotenv
import uuid
import os
import uvicorn
import base64
import json
import mimetypes
from classes.Reciept import Receipt

# Load environment variables from .env file
load_dotenv()

client =  Groq(api_key=os.environ.get("GROQ_API_KEY"))


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    with open(file.filename, "wb") as f:
        f.write(contents)

    return {"filename": file.filename}


@app.post("/read-uploaded-image/")
async def detect_image(file: UploadFile = File(...)):
    try:
        image = await file.read()
        base64_image = base64.b64encode(image).decode("utf-8")
        mime_type = file.content_type

        chat_completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                            **Objective:** Analyze the provided image. If it is a receipt, extract key information, including any applied discounts, enrich it with an inferred expense category, and return the data strictly as a JSON object. If the image is not a receipt, return the JSON literal `null`.

                            **Instructions:**

                            1.  **Image Type Verification:**
                                *   Examine the image to determine if it is a sales receipt or invoice.
                                *   If the image is NOT a receipt (e.g., it's a landscape photo, a document unrelated to a transaction, a drawing, etc.), your entire output **MUST** be the JSON literal `null`. Do not include any other text or explanation.

                            2.  **Data Extraction (If Receipt):**
                                *   If the image IS identified as a receipt, extract the following fields:
                                    *   `merchant_name`: (String) The name of the business or seller.
                                    *   `merchant_address`: (String, optional) The physical address of the merchant, if available.
                                    *   `transaction_date`: (String) The date of the transaction. Standardize to "YYYY-MM-DD" format if possible.
                                    *   `transaction_time`: (String, optional) The time of the transaction. Standardize to "HH:MM:SS" format if possible.
                                    *   `line_items`: (Array of Objects) Each object should represent a purchased item or service and contain:
                                        *   `description`: (String) Name or description of the item/service.
                                        *   `quantity`: (Number) The quantity of the item (default to 1 if not specified).
                                        *   `original_unit_price`: (Number) The price of a single unit of the item *before* any line-item specific discounts.
                                        *   `line_item_discount_amount`: (Number, optional) The total discount amount applied specifically to this line item (represented as a positive number).
                                        *   `line_item_discount_description`: (String, optional) Description of the line-item discount, if any (e.g., "20% off", "Sale").
                                        *   `total_price`: (Number) The final price for this line item after its specific discount: `(original_unit_price * quantity) - line_item_discount_amount`. If no discount, `total_price` is `original_unit_price * quantity`.
                                    *   `subtotal`: (Number, optional) The sum of all `line_items.total_price` *before* any overall discounts, taxes, or tips are applied.
                                    *   `overall_discounts`: (Array of Objects, optional) Each object representing a discount applied to the subtotal:
                                        *   `description`: (String) Description of the discount (e.g., "Coupon", "Loyalty Discount", "10% Off Total").
                                        *   `amount`: (Number) The amount of the discount (represented as a positive number).
                                    *   `tax_amount`: (Number, optional) The total amount of tax charged. If multiple taxes, sum them.
                                    *   `tip_amount`: (Number, optional) The amount of tip, if specified.
                                    *   `total_amount`: (Number) The final amount paid. This should be the most prominent total on the receipt.
                                    *   `currency_code`: (String, optional) The ISO 4217 currency code (e.g., "USD", "EUR", "GBP"). Infer if possible (e.g., from currency symbols or merchant location).
                                    *   `payment_method`: (String, optional) The method of payment (e.g., "Cash", "Credit Card", "Visa ****1234"), if visible.

                            3.  **Data Enrichment (If Receipt):**
                                *   `expense_category`: (String) Based on the `merchant_name` and `line_items`, infer an appropriate expense category. Choose from a predefined list. Examples:
                                    *   "Food & Dining"
                                    *   "Groceries"
                                    *   "Transportation"
                                    *   "Utilities"
                                    *   "Shopping"
                                    *   "Entertainment"
                                    *   "Office Supplies"
                                    *   "Travel"
                                    *   "Healthcare"
                                    *   "Services"
                                    *   "Other"

                            4.  **Output Format:**
                                *   The output **MUST** be a single, valid JSON object.
                                *   If the image is not a receipt, the output **MUST** be the JSON literal `null`.
                                *   Use `snake_case` for all JSON keys.
                                *   Ensure all monetary values are represented as numbers (integers or floats), not strings containing currency symbols. Discount amounts should be positive numbers.
                                *   If a field is optional and not found, omit it from the JSON or set its value to `null` (the JSON literal, not the string "null"), unless specified otherwise (e.g. `quantity` defaults to 1).

                            **Example of desired JSON output for a receipt (with discounts):**
                            ```json
                            {
                            "merchant_name": "Tech Gadgets Store",
                            "merchant_address": "456 Innovation Dr, Silicon City, TX 75001",
                            "transaction_date": "2023-11-15",
                            "transaction_time": "14:30:00",
                            "line_items": [
                                {
                                "description": "Wireless Mouse",
                                "quantity": 1,
                                "original_unit_price": 25.00,
                                "line_item_discount_amount": 5.00,
                                "line_item_discount_description": "Black Friday Special",
                                "total_price": 20.00
                                },
                                {
                                "description": "USB-C Cable",
                                "quantity": 2,
                                "original_unit_price": 10.00,
                                "total_price": 20.00
                                },
                                {
                                "description": "Keyboard",
                                "quantity": 1,
                                "original_unit_price": 70.00,
                                "total_price": 70.00
                                }
                            ],
                            "subtotal": 110.00,
                            "overall_discounts": [
                                {
                                "description": "Loyalty Member 10% Off",
                                "amount": 11.00
                                },
                                {
                                "description": "Holiday Coupon",
                                "amount": 5.00
                                }
                            ],
                            "tax_amount": 7.52,
                            "tip_amount": null,
                            "total_amount": 91.52,
                            "currency_code": "USD",
                            "payment_method": "Visa ****4321",
                            "expense_category": "Shopping"
                            }

                            """,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.5,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        return {"message": chat_completion.choices[0].message.content, "receipt": json.loads(chat_completion.choices[0].message.content)}

    except Exception as e:
        return {"error": f"Could not read image: {str(e)}"}
    finally:
        await file.close()



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
