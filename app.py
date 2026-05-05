from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ============================================================
# APP CONFIGURATION
# ============================================================
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cs_players.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'cs2_secret_key_flashbang_2024'

db = SQLAlchemy(app)


# ============================================================
# MODELS (Database Tables)
# ============================================================

class Player(db.Model):
    """Stores player login credentials and account info."""
    __tablename__ = 'players'

    id          = db.Column(db.Integer, primary_key=True)
    username    = db.Column(db.String(80),  unique=True, nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password    = db.Column(db.String(200), nullable=False)
    last_login  = db.Column(db.DateTime, default=None)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-one relationship with PlayerProfile
    profile = db.relationship('PlayerProfile', backref='player', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Player {self.username}>'


class PlayerProfile(db.Model):
    """Stores extended player profile information."""
    __tablename__ = 'player_profiles'

    id          = db.Column(db.Integer, primary_key=True)
    player_id   = db.Column(db.Integer, db.ForeignKey('players.id'), unique=True, nullable=False)

    # Profile fields
    rank        = db.Column(db.String(60),  default='Unranked')
    country     = db.Column(db.String(80),  nullable=True)
    bio         = db.Column(db.Text,        nullable=True)
    updated_at  = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PlayerProfile player_id={self.player_id} rank={self.rank}>'


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Serve the main frontend page."""
    return render_template('index.html')


# ------ REGISTER ------
@app.route('/register', methods=['POST'])
def register():
    """
    Accepts: username, email, password (form data via POST)
    Creates a new Player record if username/email are unique.
    Returns: JSON success or error message.
    """
    data = request.form

    username = data.get('username', '').strip()
    email    = data.get('email',    '').strip()
    password = data.get('password', '').strip()

    # Basic validation
    if not username or not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400

    # Check for duplicate username or email
    existing = Player.query.filter(
        (Player.email == email) | (Player.username == username)
    ).first()

    if existing:
        return jsonify({'error': 'Username or email already taken.'}), 400

    # Create and save the new player
    new_player = Player(
        username=username,
        email=email,
        password=password          # In production: use werkzeug hash
    )
    db.session.add(new_player)
    db.session.commit()

    return jsonify({
        'message'   : 'Agent enlisted successfully! Welcome to the server.',
        'player_id' : new_player.id
    }), 201


# ------ LOGIN ------
@app.route('/login', methods=['POST'])
def login():
    """
    Accepts: email, password (form data via POST)
    Verifies credentials and updates last_login timestamp.
    Returns: JSON with player_id and username on success.
    """
    data = request.form

    email    = data.get('email',    '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    # Look up player by email
    player = Player.query.filter_by(email=email).first()

    if not player or player.password != password:
        return jsonify({'error': 'Invalid credentials. Access denied.'}), 401

    # Update last login timestamp
    player.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message'   : 'Authentication successful. Joining server...',
        'player_id' : player.id,
        'username'  : player.username
    }), 200


# ------ SAVE PROFILE ------
@app.route('/profile/save', methods=['POST'])
def save_profile():
    """
    Accepts: player_id, rank, country, bio (form data via POST)
    Creates or updates the PlayerProfile for the given player.
    Returns: JSON success or error message.
    """
    data = request.form

    player_id = data.get('player_id')
    player    = Player.query.get(player_id)

    if not player:
        return jsonify({'error': 'Player not found.'}), 404

    # Get existing profile or create new one
    profile = player.profile or PlayerProfile(player_id=player.id)

    profile.rank    = data.get('rank',    'Unranked')
    profile.country = data.get('country', '')
    profile.bio     = data.get('bio',     '')

    db.session.add(profile)
    db.session.commit()

    return jsonify({'message': 'Profile saved successfully!'}), 200


# ------ GET PROFILE ------
@app.route('/profile/<int:player_id>', methods=['GET'])
def get_profile(player_id):
    """
    Returns the profile data for a given player_id.
    Used to load saved profile when player logs in.
    """
    player = Player.query.get_or_404(player_id)
    p      = player.profile

    if not p:
        # Return empty defaults if no profile yet
        return jsonify({
            'rank'    : 'Unranked',
            'country' : '',
            'bio'     : ''
        }), 200

    return jsonify({
        'rank'    : p.rank    or 'Unranked',
        'country' : p.country or '',
        'bio'     : p.bio     or ''
    }), 200


# ------ GET ALL PLAYERS (Admin / Debug) ------
@app.route('/players', methods=['GET'])
def get_all_players():
    """
    Returns a list of all registered players.
    Useful for testing and verifying database entries.
    """
    players = Player.query.order_by(Player.created_at.desc()).all()
    result  = []
    for p in players:
        result.append({
            'id'         : p.id,
            'username'   : p.username,
            'email'      : p.email,
            'last_login' : str(p.last_login) if p.last_login else 'Never',
            'created_at' : str(p.created_at),
            'has_profile': p.profile is not None
        })
    return jsonify({'players': result, 'total': len(result)}), 200


# ============================================================
# CREATE TABLES & RUN APP
# ============================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('========================================')
        print('  CS2 Player Database initialized!')
        print('  Tables: players, player_profiles')
        print('========================================')
    app.run(debug=True)
