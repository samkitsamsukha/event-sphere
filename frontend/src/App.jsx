import { useEffect, useState } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, clearToken, getToken, setToken } from './api'
import './App.css'

const formatDate = (value) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

function LoadingSpinner() { return <div className="spinner" role="status" aria-label="Loading" /> }
function EmptyState({ children }) { return <div className="empty-state">{children}</div> }
function ErrorState({ message }) { return <div className="error-state">{message || 'Something went wrong.'}</div> }

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))
  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then((response) => setUser(response.data)).catch(clearToken).finally(() => setLoading(false))
    const handleUnauthorized = () => setUser(null)
    window.addEventListener('eventsphere:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('eventsphere:unauthorized', handleUnauthorized)
  }, [])
  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setToken(data.access_token)
    setUser((await api.get('/auth/me')).data)
  }
  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload)
    setToken(data.access_token)
    setUser((await api.get('/auth/me')).data)
  }
  const logout = () => { clearToken(); setUser(null) }
  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}

import { createContext, useContext } from 'react'
const AuthContext = createContext(null)
const useAuth = () => useContext(AuthContext)

function Navbar() {
  const { user, logout } = useAuth()
  return <header className="navbar"><Link className="brand" to="/">Event<span>Sphere</span></Link><nav>
    <Link to="/explore">Explore</Link>{user && <Link to="/home">Home</Link>}{user?.role === 'PUBLISHER' && <Link to="/publisher">Publisher</Link>}
    {user ? <><Link to="/saved">Saved</Link><Link to="/profile">{user.name}</Link><button className="link-button" onClick={logout}>Log out</button></> : <><Link to="/login">Log in</Link><Link className="button small" to="/register">Join free</Link></>}
  </nav></header>
}

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to="/home" replace />
  return children
}

function EventCard({ event, onChanged }) {
  const { user } = useAuth()
  const [saved, setSaved] = useState(() => JSON.parse(localStorage.getItem('eventsphere_saved') || '[]').includes(event.id))
  const track = (type) => user && api.post('/interactions', { event_id: event.id, interaction_type: type }).catch(() => {})
  const toggleSave = async () => {
    if (!user) return
    if (!saved) await track('SAVE')
    const ids = JSON.parse(localStorage.getItem('eventsphere_saved') || '[]')
    localStorage.setItem('eventsphere_saved', JSON.stringify(saved ? ids.filter((id) => id !== event.id) : [...new Set([...ids, event.id])]))
    setSaved(!saved); onChanged?.()
  }
  const register = async () => { if (!user) return; await track('REGISTER'); const ids = JSON.parse(localStorage.getItem('eventsphere_registered') || '[]'); localStorage.setItem('eventsphere_registered', JSON.stringify([...new Set([...ids, event.id])])) }
  return <article className="event-card">
    <div className="card-top"><span className="eyebrow">{event.category || 'Community'}</span><button className={`save ${saved ? 'saved' : ''}`} aria-label="Save event" onClick={toggleSave}>{saved ? '♥' : '♡'}</button></div>
    <Link to={`/events/${event.id}`} onClick={() => track('CLICK')}><h3>{event.title}</h3></Link>
    <p className="muted">{event.description}</p><p className="event-meta">◷ {formatDate(event.start_time)}</p><p className="event-meta">⌖ {event.location || 'Online'}</p>
    <div className="card-footer"><span className="tag">{event.tags?.[0] || 'Event'}</span>{user && <button className="text-action" onClick={register}>Register interest →</button>}</div>
  </article>
}

function EventGrid({ events, empty = 'No events found.', onChanged }) {
  if (!events.length) return <EmptyState>{empty}</EmptyState>
  return <div className="event-grid">{events.map((event) => <EventCard key={event.id} event={event} onChanged={onChanged} />)}</div>
}

function SearchBar({ initial = '', onSearch }) {
  const [value, setValue] = useState(initial)
  return <form className="search-bar" onSubmit={(e) => { e.preventDefault(); onSearch(value) }}><span>⌕</span><input aria-label="Search events" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Search events, topics, or places" /><button className="button">Search</button></form>
}

function Filters({ params, setParams }) {
  return <div className="filters"><select aria-label="Category" value={params.get('category') || ''} onChange={(e) => setParams({ category: e.target.value })}><option value="">All categories</option><option>Technology</option><option>Music</option><option>Design</option><option>Education</option></select><input aria-label="Location" value={params.get('location') || ''} placeholder="Location" onChange={(e) => setParams({ location: e.target.value })} /><input aria-label="Start date" type="date" value={params.get('start_date') || ''} onChange={(e) => setParams({ start_date: e.target.value })} /></div>
}

function Explore() {
  const [params, setSearchParams] = useSearchParams(); const [events, setEvents] = useState([]); const [state, setState] = useState({ loading: true, error: '' })
  const setParams = (values) => { const next = new URLSearchParams(params); Object.entries(values).forEach(([key, value]) => value ? next.set(key, value) : next.delete(key)); setSearchParams(next) }
  const query = params.toString()
  useEffect(() => { api.get('/events', { params: Object.fromEntries(new URLSearchParams(query)) }).then(({ data }) => { setEvents(data); setState({ loading: false, error: '' }) }).catch((e) => setState({ loading: false, error: e.message })) }, [query])
  return <Page><div className="page-heading"><div><span className="eyebrow">DISCOVER</span><h1>Find your next <em>great moment.</em></h1></div></div><SearchBar initial={params.get('keyword') || ''} onSearch={(value) => setParams({ keyword: value })} /><Filters params={params} setParams={setParams} />{state.loading ? <LoadingSpinner /> : state.error ? <ErrorState message={state.error} /> : <EventGrid events={events} />}</Page>
}

function EventDetails() {
  const { id } = useParams(); const { user } = useAuth(); const [event, setEvent] = useState(null); const [error, setError] = useState('')
  useEffect(() => { api.get(`/events/${id}`).then(({ data }) => { setEvent(data); if (user) api.post('/interactions', { event_id: data.id, interaction_type: 'VIEW' }).catch(() => {}) }).catch((e) => setError(e.response?.data?.detail || 'Event not found')) }, [id, user])
  if (error) return <Page><ErrorState message={error} /></Page>; if (!event) return <Page><LoadingSpinner /></Page>
  return <Page><Link className="back" to="/explore">← Back to explore</Link><div className="detail"><span className="eyebrow">{event.category || 'Event'}</span><h1>{event.title}</h1><p className="lead">{event.description}</p><div className="detail-facts"><span>◷ {formatDate(event.start_time)}</span><span>⌖ {event.location || 'Online'}</span><span>Capacity: {event.capacity || 'Open'}</span></div>{user && <button className="button" onClick={() => api.post('/interactions', { event_id: event.id, interaction_type: 'REGISTER' })}>Register for event</button>}<div className="detail-copy"><h2>About this event</h2><p>{event.description}</p><div className="tags">{event.tags?.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div></div></div></Page>
}

function AuthForm({ register = false }) {
  const { login, register: signup } = useAuth(); const navigate = useNavigate(); const [form, setForm] = useState({ name: '', email: '', password: '', role: 'CUSTOMER' }); const [error, setError] = useState('')
  const submit = async (e) => { e.preventDefault(); setError(''); try { register ? await signup(form) : await login(form.email, form.password); navigate('/home') } catch (err) { setError(err.response?.data?.detail || 'Unable to continue') } }
  return <Page narrow><div className="auth-card"><span className="eyebrow">{register ? 'WELCOME IN' : 'WELCOME BACK'}</span><h1>{register ? 'Create your account.' : 'Sign in to explore.'}</h1><form onSubmit={submit}>{register && <input required minLength="2" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />}<input required type="email" placeholder="Email address" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /><input required minLength="8" type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />{register && <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="CUSTOMER">I want to discover events</option><option value="PUBLISHER">I want to publish events</option></select>}{error && <ErrorState message={error} />}<button className="button full">{register ? 'Create account' : 'Log in'} →</button></form><p className="muted">{register ? 'Already a member?' : 'New to EventSphere?'} <Link to={register ? '/login' : '/register'}>{register ? 'Log in' : 'Create an account'}</Link></p></div></Page>
}

function Home() {
  const [recommended, setRecommended] = useState([]); const [upcoming, setUpcoming] = useState([])
  useEffect(() => { api.get('/recommendations').then(({ data }) => setRecommended(data)).catch(() => {}); api.get('/events', { params: { page_size: 6 } }).then(({ data }) => setUpcoming(data)).catch(() => {}) }, [])
  return <Page><div className="hero-copy"><span className="eyebrow">YOUR EVENT UNIVERSE</span><h1>Good things happen<br /><em>when you show up.</em></h1><p>Discover gatherings shaped around your interests, your city, and what you want to explore next.</p><Link className="button" to="/explore">Explore events →</Link></div><Section title="Recommended for you" action={recommended.length ? null : 'Choose interests to personalize'}><EventGrid events={recommended} empty="We’re warming up your recommendations. Explore an event or choose interests to get started." /></Section><Section title="Upcoming events"><EventGrid events={upcoming} /></Section></Page>
}
function Section({ title, action, children }) { return <section className="section"><div className="section-heading"><h2>{title}</h2>{action && <Link to="/profile">{action} →</Link>}</div>{children}</section> }

function Profile() { const { user } = useAuth(); const [interests, setInterests] = useState([]); const [name, setName] = useState(user.name); useEffect(() => { api.get('/users/me/interests').then(({ data }) => setInterests(data)) }, []); const save = async (e) => { e.preventDefault(); await api.put('/users/me', { name }); }; return <Page><div className="page-heading"><span className="eyebrow">YOUR SPACE</span><h1>Profile & interests.</h1></div><div className="profile-layout"><form className="panel" onSubmit={save}><h2>Profile</h2><label>Name<input value={name} onChange={(e) => setName(e.target.value)} /></label><label>Email<input disabled value={user.email} /></label><button className="button">Save changes</button></form><div className="panel"><h2>Interests</h2><div className="tags">{interests.map((item) => <span className="tag" key={item.id}>{item.name}</span>)}</div><p className="muted">Your interests help shape recommendations.</p></div></div></Page> }

function Publisher() { const [events, setEvents] = useState([]); const [form, setForm] = useState({ title: '', description: '', category: '', location: '', start_time: '', end_time: '', capacity: '' }); const load = () => api.get('/events/mine').then(({ data }) => setEvents(data)); useEffect(load, []); const create = async (e) => { e.preventDefault(); await api.post('/events', { ...form, capacity: form.capacity ? Number(form.capacity) : null, tags: [] }); setForm({ title: '', description: '', category: '', location: '', start_time: '', end_time: '', capacity: '' }); load() }; const transition = async (id, action) => { await api.post(`/events/${id}/${action}`); load() }; return <Page><div className="page-heading"><span className="eyebrow">PUBLISHER STUDIO</span><h1>Build something people<br /><em>will remember.</em></h1></div><div className="publisher-layout"><form className="panel" onSubmit={create}><h2>Create event</h2>{['title', 'description', 'category', 'location', 'start_time', 'end_time', 'capacity'].map((field) => <input key={field} required={['title', 'description', 'start_time', 'end_time'].includes(field)} type={field.includes('time') ? 'datetime-local' : field === 'capacity' ? 'number' : 'text'} placeholder={field.replace('_', ' ')} value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })} />)}<button className="button full">Save draft →</button></form><div className="panel"><h2>My events</h2>{events.map((event) => <div className="publisher-event" key={event.id}><div><strong>{event.title}</strong><span className={`status ${event.status.toLowerCase()}`}>{event.status}</span></div><div>{event.status === 'DRAFT' && <Link className="text-action" to={`/publisher/events/${event.id}/edit`}>Edit</Link>}{event.status === 'DRAFT' && <button className="text-action" onClick={() => transition(event.id, 'publish')}>Publish</button>}{event.status === 'PUBLISHED' && <button className="text-action" onClick={() => transition(event.id, 'cancel')}>Cancel</button>}</div></div>)}{!events.length && <EmptyState>No events yet.</EmptyState>}</div></div></Page> }

function EditEvent() { const { id } = useParams(); const navigate = useNavigate(); const [form, setForm] = useState(null); const [error, setError] = useState(''); useEffect(() => { api.get(`/events/${id}`).then(({ data }) => setForm(data)).catch(() => api.get('/events/mine').then(({ data }) => setForm(data.find((item) => item.id === Number(id))))); }, [id]); if (!form) return <Page><LoadingSpinner /></Page>; const save = async (e) => { e.preventDefault(); try { await api.put(`/events/${id}`, { title: form.title, description: form.description, category: form.category, location: form.location, capacity: form.capacity, tags: form.tags || [], start_time: form.start_time, end_time: form.end_time }); navigate('/publisher') } catch (err) { setError(err.response?.data?.detail || 'Unable to save event') } }; return <Page><div className="panel narrow"><h2>Edit event</h2>{['title', 'description', 'category', 'location', 'start_time', 'end_time', 'capacity'].map((field) => <input key={field} required={['title', 'description', 'start_time', 'end_time'].includes(field)} type={field.includes('time') ? 'datetime-local' : field === 'capacity' ? 'number' : 'text'} value={form[field] || ''} onChange={(e) => setForm({ ...form, [field]: e.target.value })} />)}{error && <ErrorState message={error} />}<button className="button full" onClick={save}>Save changes</button></div></Page> }

function LocalEventList({ storageKey, title, empty }) {
  const [events, setEvents] = useState([])
  useEffect(() => { const ids = JSON.parse(localStorage.getItem(storageKey) || '[]'); if (!ids.length) return; Promise.all(ids.map((id) => api.get(`/events/${id}`).then(({ data }) => data).catch(() => null))).then((values) => setEvents(values.filter(Boolean))) }, [storageKey])
  return <Page><div className="page-heading"><span className="eyebrow">YOUR COLLECTION</span><h1>{title}</h1></div><EventGrid events={events} empty={empty} /></Page>
}

function Page({ children, narrow = false }) { return <><Navbar /><main className={narrow ? 'page narrow' : 'page'}>{children}</main><footer>EventSphere · Find your people, places, and moments.</footer></> }
function Landing() { return <Page><div className="landing"><span className="eyebrow">THE WORLD IS FULL OF MOMENTS</span><h1>Meet your next<br /><em>favorite thing.</em></h1><p>EventSphere makes it easier to find meaningful events, communities, and experiences tailored to you.</p><div><Link className="button" to="/explore">Start exploring →</Link><Link className="button ghost" to="/register">Create account</Link></div></div></Page> }

export default function App() {
  return <BrowserRouter><AuthProvider><Routes><Route path="/" element={<Landing />} /><Route path="/login" element={<AuthForm />} /><Route path="/register" element={<AuthForm register />} /><Route path="/explore" element={<Explore />} /><Route path="/events/:id" element={<EventDetails />} /><Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} /><Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} /><Route path="/saved" element={<ProtectedRoute><LocalEventList storageKey="eventsphere_saved" title="Saved events." empty="Save events from explore to find them here." /></ProtectedRoute>} /><Route path="/registered" element={<ProtectedRoute><LocalEventList storageKey="eventsphere_registered" title="Registered events." empty="Your registered events will appear here." /></ProtectedRoute>} /><Route path="/publisher" element={<ProtectedRoute role="PUBLISHER"><Publisher /></ProtectedRoute>} /><Route path="/publisher/events/:id/edit" element={<ProtectedRoute role="PUBLISHER"><EditEvent /></ProtectedRoute>} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></AuthProvider></BrowserRouter>
}
