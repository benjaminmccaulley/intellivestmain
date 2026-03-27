// =============================================================================
// INTELLIVEST @ TEXAS A&M — app.js
// =============================================================================
//
// BEFORE THIS FILE WILL WORK, add these 3 script tags to the <head> of EVERY
// HTML page (sign-in.html, create-account.html, index.html, etc.),
// placing them ABOVE your existing <script src="./app.js"> line:
//
//   <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
//   <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
//   <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js"></script>
//
// =============================================================================


// =============================================================================
// SECTION 1 — FIREBASE CONFIGURATION & INITIALIZATION
// =============================================================================
// These values come from Firebase Console → Project Settings → Your Apps.
// They are safe to include in frontend code — Firebase security is enforced
// through Firestore Rules on the server side, not by hiding these keys.

const firebaseConfig = {
    apiKey: "AIzaSyDbgDbMti-V1CcWJSd8_AN9L8zwAwDUw90",
    authDomain: "intellivest-authentication-db.firebaseapp.com",
    projectId: "intellivest-authentication-db",
    storageBucket: "intellivest-authentication-db.firebasestorage.app",
    messagingSenderId: "686987066379",
    appId: "1:686987066379:web:8b530c75ed6c5dd2805b0e",
    measurementId: "G-76T42QVKYV"
};

// Initialize the Firebase app — must happen once before anything else
firebase.initializeApp(firebaseConfig);

// auth → handles account creation, login, and logout
//        passwords are automatically hashed by Firebase; we never store plaintext
// db   → Firestore cloud database; stores username/profile info since
//        Firebase Auth only natively stores email + password
const auth = firebase.auth();
const db = firebase.firestore();


// =============================================================================
// SECTION 2 — AUTH OBJECT
// =============================================================================
// Replaces the old localStorage-based Auth object entirely.
// All methods are async because they make network calls to Firebase.

const Auth = {

    // ---------------------------------------------------------------------------
    // Auth.create()
    // Creates a brand-new user account. Called by the signup form.
    //
    // Flow:
    //   1. Check Firestore to make sure the username isn't already taken
    //   2. Create the account in Firebase Auth (Firebase hashes the password)
    //   3. Save the user's profile (username, name, email) to Firestore
    // ---------------------------------------------------------------------------
    async create({ username, password, email, firstName, lastName }) {

        // Step 1 — Check username availability
        // We store one document per username in a "usernames" collection.
        // If a document already exists for this username, it's taken.
        const usernameDoc = await db.collection('usernames').doc(username).get();
        if (usernameDoc.exists) {
            throw new Error('Username already exists. Please choose another.');
        }

        // Step 2 — Create the Firebase Auth account using email + password.
        // Firebase stores a securely hashed version of the password — never plaintext.
        // On success, userCredential.user.uid is the unique ID Firebase assigned.
        const userCredential = await auth.createUserWithEmailAndPassword(email, password);
        const uid = userCredential.user.uid;

        // Step 3 — Save profile data to Firestore using a batch write.
        // A batch write means both documents are saved together — if one fails,
        // neither is saved, keeping your data consistent.
        const batch = db.batch();

        // (a) Main user profile document, keyed by Firebase UID.
        //     You and your team can view all of these in the Firebase Console
        //     under Firestore Database → users collection.
        batch.set(db.collection('users').doc(uid), {
            uid,
            username,
            email,
            firstName,
            lastName,
            createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });

        // (b) Username → UID lookup document.
        //     Needed at login time to find a user's email from their username,
        //     since Firebase Auth identifies users by email, not username.
        batch.set(db.collection('usernames').doc(username), { uid });

        // Commit both writes at once
        await batch.commit();
    },

    // ---------------------------------------------------------------------------
    // Auth.login()
    // Signs in an existing user. Called by the login form.
    //
    // Flow:
    //   1. Look up the username in Firestore to get the user's UID
    //   2. Use the UID to fetch the user's email from their profile
    //   3. Sign in via Firebase Auth using email + password
    //   4. Save a lightweight session to sessionStorage so other pages
    //      on the site know who is currently logged in
    // ---------------------------------------------------------------------------
    async login({ username, password }) {

        // Step 1 — Resolve username → UID
        const usernameDoc = await db.collection('usernames').doc(username).get();
        if (!usernameDoc.exists) {
            // Intentionally vague — don't reveal whether username vs password was wrong
            throw new Error('Invalid username or password.');
        }
        const { uid } = usernameDoc.data();

        // Step 2 — Get the email associated with this UID
        const userDoc = await db.collection('users').doc(uid).get();
        if (!userDoc.exists) {
            throw new Error('Account data not found. Please contact support.');
        }
        const { email } = userDoc.data();

        // Step 3 — Sign in with Firebase Auth
        // Firebase compares the supplied password against its stored hash.
        // Throws an error automatically if the password doesn't match.
        await auth.signInWithEmailAndPassword(email, password);

        // Step 4 — Write a session entry to sessionStorage.
        // sessionStorage automatically clears when the browser tab is closed,
        // giving us "logout on close" behaviour without any extra work.
        sessionStorage.setItem('intellivest_current_user', JSON.stringify({
            username,
            uid
        }));
    },

    // ---------------------------------------------------------------------------
    // Auth.logout()
    // Signs the current user out. Hook this to any "Sign out" button on the site:
    //   document.getElementById('logoutBtn').addEventListener('click', () => Auth.logout())
    // ---------------------------------------------------------------------------
    async logout() {
        await auth.signOut();                                      // sign out from Firebase
        sessionStorage.removeItem('intellivest_current_user');    // clear local session
        window.location.href = './sign-in.html';                  // redirect to login page
    },

    // ---------------------------------------------------------------------------
    // Auth.getCurrentUser()
    // Returns the currently logged-in user from sessionStorage, or null.
    // Use on any page to gate content behind login, e.g.:
    //
    //   const user = Auth.getCurrentUser();
    //   if (!user) window.location.href = './sign-in.html';
    //   else document.getElementById('greeting').textContent = `Hi, ${user.username}!`;
    // ---------------------------------------------------------------------------
    getCurrentUser() {
        try {
            const raw = sessionStorage.getItem('intellivest_current_user');
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }
};


// =============================================================================
// SECTION 3 — LOGIN FORM HANDLER
// =============================================================================
// Intercepts the sign-in form submission and calls Auth.login().
// The HTML form is completely unchanged — we just listen for the submit event.

(function initLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return; // this script runs on every page; bail if form isn't here

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // prevent default browser form submission / page reload

        const data = new FormData(loginForm);
        const username = (data.get('username') || '').toString().trim();
        const password = (data.get('password') || '').toString();

        // Basic presence check before hitting Firebase
        if (!username || !password) {
            alert('Please fill in all fields.');
            return;
        }

        try {
            await Auth.login({ username, password });
            alert(`Welcome back, ${username}!`);
            window.location.href = './index.html'; // redirect to home on success
        } catch (err) {
            alert(err.message || 'Login failed. Please check your credentials.');
        }
    });
})();


// =============================================================================
// SECTION 4 — SIGNUP FORM HANDLER
// =============================================================================
// Intercepts the account-creation form submission and calls Auth.create().

(function initSignupForm() {
    const signupForm = document.getElementById('signupForm');
    if (!signupForm) return; // bail if the signup form isn't on this page

    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = new FormData(signupForm);
        const payload = {
            firstName: (data.get('firstName') || '').toString().trim(),
            lastName: (data.get('lastName') || '').toString().trim(),
            email: (data.get('email') || '').toString().trim(),
            username: (data.get('username') || '').toString().trim(),
            password: (data.get('password') || '').toString(),
        };

        // Client-side validation — Firebase enforces its own rules server-side too
        if (!payload.firstName || !payload.lastName || !payload.email ||
            !payload.username || !payload.password) {
            alert('Please complete all fields.');
            return;
        }

        if (payload.password.length < 6) {
            // Firebase requires a minimum of 6 characters; catch it here for a
            // friendlier message before the request is even sent
            alert('Password must be at least 6 characters.');
            return;
        }

        try {
            await Auth.create(payload);
            alert('Account created successfully! You can now sign in.');
            window.location.href = './sign-in.html';
        } catch (err) {
            alert(err.message || 'Sign up failed. Please try again.');
        }
    });
})();


// =============================================================================
// SECTION 5 — THEME TOGGLE  (unchanged from original)
// =============================================================================
// Reads the saved theme on page load and applies it.
// Saves the user's preference to localStorage when they click the toggle.
// NOTE: localStorage is still fine for theme preference — this is not
// sensitive data and doesn't need to move to Firebase.

(function initTheme() {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') document.documentElement.classList.add('dark');

    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    toggle.addEventListener('click', () => {
        document.documentElement.classList.toggle('dark');
        const nowDark = document.documentElement.classList.contains('dark');
        localStorage.setItem('theme', nowDark ? 'dark' : 'light');
    });
})();


// =============================================================================
// SECTION 6 — CUSTOM CURSOR  (unchanged from original)
// =============================================================================
// Renders a blue dot that smoothly follows the mouse using requestAnimationFrame.
// Grows larger when hovering over interactive elements (links, buttons, inputs).

(function initCursor() {
    const cursor = document.getElementById('cursor');
    if (!cursor) return;

    let x = window.innerWidth / 2, y = window.innerHeight / 2;
    let tx = x, ty = y;
    const speed = 0.15;
    let rafId = null;

    function updateCursor(e) {
        tx = e.clientX;
        ty = e.clientY;
        cursor.style.opacity = '0.9';
    }

    window.addEventListener('mousemove', updateCursor);
    window.addEventListener('mouseleave', () => {
        cursor.style.opacity = '0';
    });
    window.addEventListener('mouseenter', () => {
        cursor.style.opacity = '0.9';
    });

    // Smooth lag effect — cursor position eases toward the real mouse position
    function animate() {
        x += (tx - x) * speed;
        y += (ty - y) * speed;
        cursor.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        rafId = requestAnimationFrame(animate);
    }
    animate();

    // Enlarge the cursor dot when hovering over interactive elements
    const interactive = document.querySelectorAll('a, button, input, .btn, .link');
    interactive.forEach(el => {
        el.addEventListener('mouseenter', () => {
            cursor.style.width = '32px';
            cursor.style.height = '32px';
            cursor.style.marginLeft = '-16px';
            cursor.style.marginTop = '-16px';
        });
        el.addEventListener('mouseleave', () => {
            cursor.style.width = '20px';
            cursor.style.height = '20px';
            cursor.style.marginLeft = '-10px';
            cursor.style.marginTop = '-10px';
        });
    });
})();


// =============================================================================
// SECTION 7 — COPYRIGHT YEAR  (unchanged from original)
// =============================================================================
// Automatically updates the footer year so it never goes stale.

(function setYear() {
    const yearEl = document.getElementById('year');
    if (yearEl) {
        yearEl.textContent = String(new Date().getFullYear());
    }
})();
