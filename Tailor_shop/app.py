from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Temporary data storage
orders = [
    {"id": 1, "name": "Alex Rivera", "neck": 15.5, "waist": 32, "status": "In Progress"},
    {"id": 2, "name": "Sam Chen", "neck": 16, "waist": 34, "status": "Pending"}
]

@app.route('/')
def index():
    return render_template('index.html', orders=orders)

@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if request.method == 'POST':
        new_order = {
            "id": len(orders) + 1,
            "name": request.form['name'].strip(),
            "neck": float(request.form['neck']),
            "waist": float(request.form['waist']),
            "status": "Pending"
        }
        orders.append(new_order)
        return redirect(url_for('index'))
    return render_template('add_order.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
