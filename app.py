#app.py
from functools import wraps
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError
from sqlalchemy import Float, ForeignKey, Table, String, Column, UniqueConstraint, select, exc, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List, Optional
import uuid
import json, jwt
from datetime import datetime, timedelta, timezone
from  werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)

#JWT token 
app.config['SECRET_KEY'] = 'my super secret key'

# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:<password>@localhost/flask_api_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Creating our Base Model
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy and Marshmallow
db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)

#The association table between Users and Pets
order_product = Table(
	"order_product",
	Base.metadata,
	Column("order_id", ForeignKey("orders.id")),
	Column("product_id", ForeignKey("products.id")),
    UniqueConstraint('order_id', 'product_id', name='unique_product_order')
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[Optional[str]] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(String(95))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password: Mapped[str] = mapped_column(String(200))
		
	#One-to-Many relationship from this User to a List of Pet Objects
    orders: Mapped[List["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")
   
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
		
    #Many-to-Many relationship
    products: Mapped[List["Product"]] = relationship(secondary=order_product, back_populates="orders_to_product")
    #Many-to-One relationship
    user: Mapped["User"] = relationship(back_populates="orders")

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Float)
		
    #Many-to-Many relationship
    orders_to_product: Mapped[List["Order"]] = relationship(secondary=order_product, back_populates="products")

#=======  Schemas ========
# User Schema
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        
# Order Schema
class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order

# Product Schema
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product

# Initialize Schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True) #Can serialize many User objects (a list of them)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401
  
        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            query = select(User).where(User.public_id == data['public_id'])
            current_user = db.session.execute(query).scalars().first()
        except:
            return jsonify({
                'message' : 'Token is invalid !!'
            }), 401
        # returns the current logged in users context to the routes
        return  f(current_user, *args, **kwargs)
  
    return decorated

#======== User Routes =========
# route for logging user in
@app.route('/login', methods =['POST'])
def login():
    # creates dictionary of form data
    auth = request.json
  
    if not auth or not auth.get('email') or not auth.get('password'):
        # returns 401 if any email or / and password is missing
        return jsonify({"message": f"Missing required fields"}), 401
  
    query = select(User).where(User.email == auth.get('email'))
    user = db.session.execute(query).scalars().first()
    if not user:
        # returns 401 if user does not exist
        return jsonify({"message": f"User doesn't exist"}), 401
  
    if check_password_hash(user.password, auth.get('password')):
        # generates the JWT Token
        token = jwt.encode({
            'public_id': user.public_id,
            'exp' : datetime.now(timezone.utc) + timedelta(minutes = 30)
        }, app.config['SECRET_KEY'])
  
        return jsonify({'token' : token}), 201
    # returns 403 if password is wrong
    return jsonify({"message": f"Couldn't verify password"}), 403

@app.route('/users', methods=['POST'])
def create_user():
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    try:
        new_user = User(name=user_data['name'], address=user_data['address'], email=user_data['email'], password=generate_password_hash(user_data['password']), public_id=str(uuid.uuid4()))
        db.session.add(new_user)
        db.session.commit()
    except exc.IntegrityError as e:
        return jsonify({"message": f"Duplicate email {user_data['email']}"}), 400

    return user_schema.jsonify({
            'public_id': new_user.public_id,
            'name' : new_user.name,
            'email' : new_user.email,
            'address' : new_user.address
        }), 201

@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    page = request.args.get('page')
    query = select(User).order_by(User.id)
    if page:
        users = db.paginate(query, page=int(page), per_page=20, error_out=False).items
    else:
        users = db.session.execute(query).scalars().all()
    # converting the query objects
    # to list of jsons
    output = []
    for user in users:
        # appending the user data json 
        # to the response list
        output.append({
            'public_id': user.public_id,
            'name' : user.name,
            'email' : user.email,
            'address' : user.address
        })
    return users_schema.jsonify(output), 200

@app.route('/users/<int:id>', methods=['GET'])
@token_required
def get_user(current_user, id):
    user = db.session.get(User, id)
    return user_schema.jsonify({
            'public_id': user.public_id,
            'name' : user.name,
            'email' : user.email,
            'address' : user.address
        }), 200

@app.route('/users/<int:id>', methods=['PUT'])
@token_required
def update_user(current_user, id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"message": "Invalid user id"}), 400
    
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    user.name = user_data['name']
    user.email = user_data['email']
    user.address = user_data['address']
    user.password = generate_password_hash(user.password['password'])
    user.public_id=str(uuid.uuid4())

    db.session.commit()
    return user_schema.jsonify({
            'public_id': user.public_id,
            'name' : user.name,
            'email' : user.email,
            'address' : user.address
        }), 200

@app.route('/users/<int:id>', methods=['DELETE'])
@token_required
def delete_user(current_user, id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"message": "Invalid user id"}), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"succefully deleted user {id}"}), 200

#  ======== Product Routes ========
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    new_product = Product(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return product_schema.jsonify(new_product), 201

@app.route('/products', methods=['GET'])
def get_products():
    page = request.args.get('page')
    query = select(Product).order_by(Product.id)
    if page:
        products = db.paginate(query, page=int(page), per_page=20, error_out=False).items
    else:
        products = db.session.execute(query).scalars().all()

    return products_schema.jsonify(products), 200

@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = db.session.get(Product, id)
    return product_schema.jsonify(product), 200

@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Invalid prodct id"}), 400
    
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']

    db.session.commit()
    return product_schema.jsonify(product), 200

@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"succefully deleted product {id}"}), 200

#  ======== Order Routes ========

@app.route('/orders', methods=['POST'])
def create_order():
    try:
        if 'user_id' not in request.json:
            return jsonify("provide a user_id"), 400
        user_id = request.json['user_id']
        del request.json['user_id']
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "Invalid user id"}), 400
    new_order = Order(order_date=order_data['order_date'], user_id=user_id)
    db.session.add(new_order)
    db.session.commit()
    
    return order_schema.jsonify(new_order), 201

@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['GET'])
def add_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    try:
        product_name = product.product_name
        order.products.append(product)
        db.session.commit()
    except exc.IntegrityError as e:
        return jsonify({"message": f"Duplicate proudct {product_name} for order {order_id}"}), 400
    
    return jsonify({"message": f"{product.product_name} added to order {order_id}!"}), 200

@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"message": "Invalid product id"}), 400

    order.products.remove(product)
    db.session.commit()
    
    return jsonify({"message": f"{product.product_name} removed from order {order_id}!"}), 200

@app.route('/orders/user/<int:user_id>', methods=['GET'])
def get_orders_for_user(user_id):
    query = select(Order).where(Order.user_id == user_id)
    orders = db.session.execute(query).scalars().all()

    return orders_schema.jsonify(orders), 200

@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_products_for_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    
    return products_schema.jsonify(order.products), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)