
import pymongo
from pymongo.errors import ConnectionFailure

def test_mongodb_connection():
    try:
        # Thử kết nối đến MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        
        # Thực hiện lệnh ping để kiểm tra kết nối
        client.admin.command("ping")
        print("Kết nối với MongoDB thành công!")
        
        # In danh sách cơ sở dữ liệu (tùy chọn)
        print("Danh sách cơ sở dữ liệu:", client.list_database_names())
        return True
    
    except ConnectionFailure as e:
        print("Không thể kết nối với MongoDB. Lỗi:", e)
        return False
    except Exception as e:
        print("Đã xảy ra lỗi:", e)
        return False

if __name__ == "__main__":
    test_mongodb_connection()
