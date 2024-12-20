# RestAPI
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:<password>@localhost/flask_api_db' will need a db called flask_api_db and replace <password> with you password

routes available:
===== user routes =====

@app.route('/login', methods =['POST']) will be how you get access token
    ex. {
        "email": "whatever@me.com",
        "password": "blah"
        }

@app.route('/users', methods=['POST']) creates a new user
    ex. {
        "email": "whatever@me.com",
        "password": "blah"
        "address": "123 cool street"
        "name": "john doe"
        }

@app.route('/users', methods=['GET']) requires token in x-access-token header and returns all users
@app.route('/users/<int:id>', methods=['GET']) requires token in x-access-token header and return user with id specified in url
@app.route('/users/<int:id>', methods=['PUT']) requires token in x-access-token header and updates user with id specified in url
    ex. {
        "email": "whatever@me.com",
        "password": "blah"
        "address": "123 cool street"
        "name": "john doe"
        }
@app.route('/users/<int:id>', methods=['DELETE']) requires token in x-access-token header and deletes user with id specified in url
@app.route('/products', methods=['POST']) creates new product
    ex. {
        "proudct_name": "pickle",
        "price": "25.25"
        }

===== product routes =====

@app.route('/products', methods=['GET']) returns all available products
@app.route('/products/<int:id>', methods=['GET']) returns product with id specified in url
@app.route('/products/<int:id>', methods=['PUT']) updates product with id specified in url
@app.route('/products/<int:id>', methods=['DELETE']) deletes product with id specified in url

===== order routes =====

@app.route('/orders', methods=['POST']) create new order 
    ex. {
        "user_id": "1",
        "order_date": "2021-09-09 15:44:15.81785"
        }
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['GET']) adds specified product by id in url to order by id specified in url
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE']) removes specified product by id in url to order by id specified in url
@app.route('/orders/user/<int:user_id>', methods=['GET']) returns all orders for specified user by id in url
@app.route('/orders/<int:order_id>/products', methods=['GET']) returns all products for specified order by id in url