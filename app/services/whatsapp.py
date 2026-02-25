import httpx

class WhatsAppService:
    def __init__(self, api_url: str, token: str, instance: str):
        self.api_url = api_url
        self.token = token
        self.instance = instance

    async def send_message(self, phone: str, text: str):
        headers = {
            "apikey": f"{self.token}"
        }
        data = {
            "number": phone, 
            "text": text
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.api_url}/sendText/{self.instance}", headers=headers, json=data)
        except httpx.HTTPError as e:
            print("whatsapp")
            print(f"Error sending WhatsApp message: {e}")
            print("*" * 20)
            raise

    async def send_message_with_url_file(self, phone: str, caption: str, file_name: str, pdf_url: str = None):
        headers = {
            "apikey": f"{self.token}"
        }
        data = {
            "number": phone, 
            "mediatype": "document",
            "mimetype": "application/pdf",
            "caption": caption,
            "media": pdf_url, # URL DO S3
            "fileName": file_name
        }
        async with httpx.AsyncClient() as client:
            uri = f"{self.api_url}/sendMedia/{self.instance}"
            await client.post(uri, headers=headers, json=data)
