import json
import os
import datetime
from datetime import datetime, timedelta
import logging

class Database:
    """Class for handling all database operations using JSON files."""
    
    def __init__(self):
        self.users_file = 'data/users.json'
        self.companies_file = 'data/companies.json'
        self.timeout_logs_file = 'data/timeout_logs.json'
        self.transaction_requests_file = 'data/transaction_requests.json'
        
        self.initialize_data_files()
        
    def initialize_data_files(self):
        """Initialize data files if they don't exist."""
        os.makedirs('data', exist_ok=True)
        
        # Initialize users file
        if not os.path.exists(self.users_file):
            self.save_json(self.users_file, {})
            
        # Initialize companies file
        if not os.path.exists(self.companies_file):
            self.save_json(self.companies_file, {"next_id": 1, "companies": []})
            
        # Initialize timeout logs file
        if not os.path.exists(self.timeout_logs_file):
            self.save_json(self.timeout_logs_file, [])
            
        # Initialize transaction requests file
        if not os.path.exists(self.transaction_requests_file):
            self.save_json(self.transaction_requests_file, {
                "requests": [],
                "next_id": 1
            })
    
    def save_json(self, file_path, data):
        """Save data to a JSON file."""
        with open(file_path, 'w') as f:
            # Handle datetime objects for JSON serialization
            json.dump(data, f, default=self._json_serialize)
    
    def load_json(self, file_path):
        """Load data from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Convert string dates back to datetime objects
                return self._json_deserialize(data)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            logging.error(f"Error parsing JSON from {file_path}")
            return None
    
    def _json_serialize(self, obj):
        """Helper method to serialize datetime objects for JSON."""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        return obj
    
    def _json_deserialize(self, obj):
        """Helper method to deserialize datetime objects from JSON."""
        if isinstance(obj, dict):
            if "__datetime__" in obj:
                return datetime.fromisoformat(obj["__datetime__"])
            return {k: self._json_deserialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._json_deserialize(item) for item in obj]
        return obj
    
    def get_or_create_user(self, user_id):
        """Get a user's data or create a new user if they don't exist."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            # Create new user
            users[user_id_str] = {
                "wallet": 0,
                "bank": 0,
                "last_daily": None,
                "company_id": None,
                "last_activity": datetime.now().isoformat()
            }
            self.save_json(self.users_file, users)
            
        return users[user_id_str]
    
    def add_money(self, user_id, amount):
        """Add money to a user's wallet."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            self.get_or_create_user(user_id)
            
        users[user_id_str]["wallet"] += amount
        self.save_json(self.users_file, users)
        
        return {"success": True, "new_balance": users[user_id_str]["wallet"]}
    
    def remove_money(self, user_id, amount):
        """Remove money from a user's wallet if they have enough."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            return {"success": False, "message": "User not found"}
            
        if users[user_id_str]["wallet"] < amount:
            return {"success": False, "message": "Not enough money in wallet"}
            
        users[user_id_str]["wallet"] -= amount
        self.save_json(self.users_file, users)
        
        return {"success": True, "new_balance": users[user_id_str]["wallet"]}
    
    def claim_daily_reward(self, user_id):
        """Claim the daily reward of $100 if available."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            self.get_or_create_user(user_id)
            
        now = datetime.now()
        
        # If user has never claimed or claimed yesterday or earlier
        if (not users[user_id_str]["last_daily"] or 
            datetime.fromisoformat(users[user_id_str]["last_daily"]).date() < now.date()):
            
            users[user_id_str]["wallet"] += 100
            users[user_id_str]["last_daily"] = now.isoformat()
            self.save_json(self.users_file, users)
            
            return {"success": True, "new_balance": users[user_id_str]["wallet"]}
        else:
            # Calculate time until next reward
            last_claim = datetime.fromisoformat(users[user_id_str]["last_daily"])
            next_available = datetime.combine(last_claim.date() + timedelta(days=1), 
                                             datetime.min.time())
            
            return {"success": False, "next_available": next_available}
    
    def give_daily_rewards_to_all(self):
        """Give daily rewards to all users at once."""
        users = self.load_json(self.users_file)
        now = datetime.now()
        
        for user_id in users:
            users[user_id]["wallet"] += 100
            users[user_id]["last_daily"] = now.isoformat()
            
        self.save_json(self.users_file, users)
        logging.info(f"Daily rewards given to {len(users)} users")
    
    def deposit(self, user_id, amount):
        """Deposit money from wallet to bank."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            return {"success": False, "message": "User not found"}
            
        if users[user_id_str]["wallet"] < amount:
            return {"success": False, "message": "Not enough money in wallet"}
            
        users[user_id_str]["wallet"] -= amount
        users[user_id_str]["bank"] += amount
        self.save_json(self.users_file, users)
        
        return {
            "success": True, 
            "wallet": users[user_id_str]["wallet"],
            "bank": users[user_id_str]["bank"]
        }
    
    def withdraw(self, user_id, amount):
        """Withdraw money from bank to wallet."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            return {"success": False, "message": "User not found"}
            
        if users[user_id_str]["bank"] < amount:
            return {"success": False, "message": "Not enough money in bank"}
            
        users[user_id_str]["bank"] -= amount
        users[user_id_str]["wallet"] += amount
        self.save_json(self.users_file, users)
        
        return {
            "success": True, 
            "wallet": users[user_id_str]["wallet"],
            "bank": users[user_id_str]["bank"]
        }
    
    def transfer(self, sender_id, recipient_id, amount):
        """Transfer money from one user to another."""
        users = self.load_json(self.users_file)
        sender_id_str = str(sender_id)
        recipient_id_str = str(recipient_id)
        
        # Create users if they don't exist
        if sender_id_str not in users:
            return {"success": False, "message": "Sender not found"}
            
        if recipient_id_str not in users:
            self.get_or_create_user(recipient_id)
            
        # Check if sender has enough money
        if users[sender_id_str]["wallet"] < amount:
            return {"success": False, "message": "Not enough money in wallet"}
            
        # Transfer the money
        users[sender_id_str]["wallet"] -= amount
        users[recipient_id_str]["wallet"] += amount
        self.save_json(self.users_file, users)
        
        return {
            "success": True,
            "sender_wallet": users[sender_id_str]["wallet"],
            "recipient_wallet": users[recipient_id_str]["wallet"]
        }
    
    def create_company(self, owner_id, company_name, creator_role_id=None):
        """Create a new company with the given owner and name.
        
        Args:
            owner_id: The user ID of the company owner
            company_name: The name of the company
            creator_role_id: The role ID that created the company (for bonus calculation)
        """
        data = self.load_json(self.companies_file)
        
        # Check if company name already exists
        for company in data["companies"]:
            if company["name"].lower() == company_name.lower():
                return {"success": False, "message": "A company with this name already exists"}
        
        # Check if user already owns a company
        for company in data["companies"]:
            if company["owner_id"] == owner_id:
                return {"success": False, "message": "You already own a company"}
                
        # Create the new company
        company_id = data["next_id"]
        data["next_id"] += 1
        
        new_company = {
            "id": company_id,
            "name": company_name,
            "owner_id": owner_id,
            "employees": [],
            "created_at": datetime.now(),
            "creator_role_id": creator_role_id
        }
        
        data["companies"].append(new_company)
        self.save_json(self.companies_file, data)
        
        # Update user's company_id
        self.update_user_company(owner_id, company_id)
        
        return {"success": True, "company_id": company_id}
    
    def get_company_by_id(self, company_id):
        """Get a company by its ID."""
        data = self.load_json(self.companies_file)
        
        for company in data["companies"]:
            if company["id"] == company_id:
                return company
                
        return None
    
    def get_company_by_name(self, company_name):
        """Get a company by its name."""
        data = self.load_json(self.companies_file)
        
        for company in data["companies"]:
            if company["name"].lower() == company_name.lower():
                return company
                
        return None
    
    def get_user_company(self, user_id):
        """Get the company a user belongs to (as owner or employee)."""
        # Check if user is a company owner
        owner_company = self.get_user_owned_company(user_id)
        if owner_company:
            return owner_company
            
        # Check if user is an employee
        data = self.load_json(self.companies_file)
        
        for company in data["companies"]:
            if user_id in company["employees"]:
                return company
                
        return None
    
    def get_user_owned_company(self, user_id):
        """Get the company owned by a user."""
        data = self.load_json(self.companies_file)
        
        for company in data["companies"]:
            if company["owner_id"] == user_id:
                return company
                
        return None
    
    def update_user_company(self, user_id, company_id):
        """Update a user's company ID."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            self.get_or_create_user(user_id)
            
        users[user_id_str]["company_id"] = company_id
        self.save_json(self.users_file, users)
    
    def add_employee_to_company(self, company_id, user_id):
        """Add a user as an employee to a company.
        
        Returns:
            dict: A dictionary with success status, and additional information:
                - success: Boolean indicating whether the operation was successful
                - message: Error message if success is False
                - unlocked_bonus: Boolean indicating whether this addition pushed the company over 5 members
                - company_name: The name of the company (only if unlocked_bonus is True)
                - creator_role_id: The ID of the role that created the company (only if unlocked_bonus is True)
        """
        data = self.load_json(self.companies_file)
        
        company_index = None
        for i, company in enumerate(data["companies"]):
            if company["id"] == company_id:
                company_index = i
                break
                
        if company_index is None:
            return {"success": False, "message": "Company not found"}
            
        # Check if user is already in the company
        if user_id in data["companies"][company_index]["employees"]:
            return {"success": False, "message": "User is already an employee of this company"}
        
        # Check if this addition will push the company over 5 members
        current_member_count = len(data["companies"][company_index]["employees"]) + 1  # +1 for owner
        unlocked_bonus = current_member_count == 5  # Will become 6 members after addition
        
        # Add user to company
        data["companies"][company_index]["employees"].append(user_id)
        self.save_json(self.companies_file, data)
        
        # Update user's company_id
        self.update_user_company(user_id, company_id)
        
        result = {"success": True, "unlocked_bonus": unlocked_bonus}
        
        # Add additional info if bonus was unlocked
        if unlocked_bonus:
            result["company_name"] = data["companies"][company_index]["name"]
            result["creator_role_id"] = data["companies"][company_index].get("creator_role_id")
            
        return result
    
    def remove_employee_from_company(self, company_id, user_id):
        """Remove a user from a company."""
        data = self.load_json(self.companies_file)
        
        company_index = None
        for i, company in enumerate(data["companies"]):
            if company["id"] == company_id:
                company_index = i
                break
                
        if company_index is None:
            return {"success": False, "message": "Company not found"}
            
        # Check if user is in the company
        if user_id not in data["companies"][company_index]["employees"]:
            return {"success": False, "message": "User is not an employee of this company"}
            
        # Remove user from company
        data["companies"][company_index]["employees"].remove(user_id)
        self.save_json(self.companies_file, data)
        
        # Update user's company_id
        self.update_user_company(user_id, None)
        
        return {"success": True}
    
    def delete_company(self, company_id):
        """Delete a company and update all related users."""
        data = self.load_json(self.companies_file)
        
        company_index = None
        company = None
        for i, c in enumerate(data["companies"]):
            if c["id"] == company_id:
                company_index = i
                company = c
                break
                
        if company_index is None:
            return {"success": False, "message": "Company not found"}
            
        # Update owner's company_id
        self.update_user_company(company["owner_id"], None)
        
        # Update all employees' company_id
        for employee_id in company["employees"]:
            self.update_user_company(employee_id, None)
            
        # Remove company
        data["companies"].pop(company_index)
        self.save_json(self.companies_file, data)
        
        return {"success": True}
    
    def get_all_companies(self):
        """Get a list of all companies."""
        data = self.load_json(self.companies_file)
        return data["companies"]
    
    def update_activity(self, user_id):
        """Update a user's activity and give them a bonus if they're in a company."""
        users = self.load_json(self.users_file)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            return
            
        user = users[user_id_str]
        now = datetime.now()
        
        # Check if user has a company
        if user["company_id"] is not None:
            # Check if last activity was more than 1 hour ago
            if user["last_activity"] and datetime.fromisoformat(user["last_activity"]) < now - timedelta(hours=1):
                # Get company info to determine bonus amount
                company = self.get_company_by_id(user["company_id"])
                if company:
                    # Default bonus
                    bonus_amount = 10
                    
                    # Calculate bonus based on creator role and company size
                    if "creator_role_id" in company:
                        # Level 35 role (25$ bonus)
                        if company["creator_role_id"] == 1352694494797234237:
                            bonus_amount = 25
                        # Level 50 role (50$ bonus)
                        elif company["creator_role_id"] == 1352694494813749299:
                            bonus_amount = 50
                    
                    # Additional bonus for companies with more than 5 members
                    total_members = len(company.get("employees", [])) + 1  # +1 for owner
                    if total_members > 5:
                        bonus_amount += 25
                        
                    # Give activity bonus
                    user["wallet"] += bonus_amount
                else:
                    # Default bonus if company not found
                    user["wallet"] += 10
                
        # Update last activity
        user["last_activity"] = now.isoformat()
        self.save_json(self.users_file, users)
    
    def get_leaderboard(self):
        """Get leaderboard data sorted by total wealth."""
        users = self.load_json(self.users_file)
        
        # Convert to list and add user_id as a field
        users_list = []
        for user_id, data in users.items():
            user_data = data.copy()
            user_data["user_id"] = int(user_id)
            users_list.append(user_data)
            
        # Sort by total wealth (wallet + bank)
        users_list.sort(key=lambda x: x["wallet"] + x["bank"], reverse=True)
        
        return users_list
    
    def add_timeout_log(self, moderator_id, user_id, duration):
        """Add a timeout log entry."""
        logs = self.load_json(self.timeout_logs_file)
        
        log_entry = {
            "moderator_id": moderator_id,
            "user_id": user_id,
            "duration": duration,
            "timestamp": datetime.now()
        }
        
        logs.append(log_entry)
        self.save_json(self.timeout_logs_file, logs)
    
    def get_timeout_logs(self, user_id):
        """Get timeout logs for a user."""
        logs = self.load_json(self.timeout_logs_file)
        
        # Filter logs for the specified user
        user_logs = [log for log in logs if log["user_id"] == user_id]
        
        # Sort by timestamp (newest first)
        user_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return user_logs
        
    def initialize_transaction_requests_file(self):
        """Initialize the transaction requests file if it doesn't exist."""
        if not os.path.exists(self.transaction_requests_file):
            self.save_json(self.transaction_requests_file, {
                "requests": [],
                "next_id": 1
            })
            
    def create_money_request(self, requester_id, recipient_id, amount, reason=None):
        """Create a money request from one user to another.
        
        Args:
            requester_id: The user ID requesting the money
            recipient_id: The user ID being asked to pay
            amount: The amount of money requested
            reason: Optional reason for the request
            
        Returns:
            dict: A dictionary with request information including an ID
        """
        self.initialize_transaction_requests_file()
        data = self.load_json(self.transaction_requests_file)
        
        # Create a new request
        request_id = data["next_id"]
        data["next_id"] += 1
        
        new_request = {
            "id": request_id,
            "requester_id": requester_id,
            "recipient_id": recipient_id,
            "amount": amount,
            "reason": reason,
            "status": "pending",  # pending, accepted, rejected
            "created_at": datetime.now(),
            "resolved_at": None
        }
        
        data["requests"].append(new_request)
        self.save_json(self.transaction_requests_file, data)
        
        return new_request
        
    def get_pending_requests(self, user_id):
        """Get all pending money requests for a user (both as requester and recipient)."""
        self.initialize_transaction_requests_file()
        data = self.load_json(self.transaction_requests_file)
        
        # Get all requests related to this user
        user_requests = [
            req for req in data["requests"] 
            if (req["requester_id"] == user_id or req["recipient_id"] == user_id)
            and req["status"] == "pending"
        ]
        
        # Sort by timestamp (newest first)
        user_requests.sort(key=lambda x: x["created_at"], reverse=True)
        
        return user_requests
        
    def get_request_by_id(self, request_id):
        """Get a money request by its ID."""
        self.initialize_transaction_requests_file()
        data = self.load_json(self.transaction_requests_file)
        
        for request in data["requests"]:
            if request["id"] == request_id:
                return request
                
        return None
        
    def resolve_money_request(self, request_id, accept=True):
        """Resolve a money request by accepting or rejecting it.
        
        Args:
            request_id: The ID of the request to resolve
            accept: Boolean indicating whether to accept the request
            
        Returns:
            dict: A dictionary with the result of the resolution
        """
        self.initialize_transaction_requests_file()
        data = self.load_json(self.transaction_requests_file)
        
        # Find the request
        request = None
        request_index = -1
        for i, req in enumerate(data["requests"]):
            if req["id"] == request_id:
                request = req
                request_index = i
                break
                
        if request is None:
            return {"success": False, "message": "Request not found"}
            
        # Check if the request is still pending
        if request["status"] != "pending":
            return {"success": False, "message": "This request has already been resolved"}
            
        # If accepting, transfer the money
        result = {"success": True, "accepted": accept}
        
        if accept:
            transfer_result = self.transfer(
                request["recipient_id"], 
                request["requester_id"], 
                request["amount"]
            )
            
            if not transfer_result["success"]:
                return {"success": False, "message": transfer_result["message"]}
                
            result["transfer"] = transfer_result
            
        # Update the request status
        data["requests"][request_index]["status"] = "accepted" if accept else "rejected"
        data["requests"][request_index]["resolved_at"] = datetime.now()
        self.save_json(self.transaction_requests_file, data)
        
        return result
        
    def log_transaction(self, sender_id, recipient_id, amount, transaction_type, message=None):
        """Log a money transaction for notification purposes.
        
        Args:
            sender_id: The user ID sending the money (or None for system transactions)
            recipient_id: The user ID receiving the money
            amount: The amount of money transferred
            transaction_type: The type of transaction (daily, transfer, quest, etc.)
            message: Optional message about the transaction
        """
        # For future implementation if needed - this would store all transaction history
        pass
