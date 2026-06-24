# # test_push.py
# import asyncio
# import firebase_admin
# from firebase_admin import credentials
# from firebase_service import send_leak_push

# async def main():
#     print("--- Direct File Initialization Test ---")
#     try:
#         cred = credentials.Certificate(r"C:\Users\DELL\Downloads\aquasense-5c86f-firebase-adminsdk-fbsvc-57eedb1293.json") 
#         firebase_admin.initialize_app(cred)
        
#         import firebase_service
#         firebase_service._initialized = True
#         print("Firebase Admin initialized directly from file ✓")
        
#     except Exception as e:
#         print(f"Direct file initialization failed: {e}")
#         return

#     print("\n--- Sending Test Push ---")
#     print("Attempting to connect to Firebase servers...")
    
#     # Running your live device token
#     token = "cw6koXJvQbWlWOBtwEVDoC:APA91bFl4BUNpeOnd-Tx5dt-D8p5REShJgLEEOG99Wp0REkncV6P-Z4YSMotgyyNlX5-YY1e20CgbmHHF5pHmnn-Y_5O3n8OWLq3t-hLyKZQI_4zD6qrsnQ"
    
#     success = await send_leak_push(token, "Kitchen Line", 1)
    
#     print(f"\nExecution Finished! Success result: {success}")

# if __name__ == "__main__":
#     asyncio.run(main())