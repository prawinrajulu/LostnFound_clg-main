import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, MapPin, Calendar, Package } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { PublicHeader } from '../components/Header';
import { itemsAPI } from '../services/api';
import bgimg from '../assets/bgimg.jpg';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://lostnfound-clg-main.onrender.com';

const PublicPage = () => {
  const [items, setItems] = useState([]);
  const [filteredItems, setFilteredItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchItems();
  }, []);

  useEffect(() => {
    // Always guard with Array.isArray before filtering
    if (!Array.isArray(items)) return;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const filtered = items.filter(item =>
        (item.description || '').toLowerCase().includes(q) ||
        (item.location || '').toLowerCase().includes(q)
      );
      setFilteredItems(filtered);
    } else {
      setFilteredItems(items);
    }
  }, [searchQuery, items]);

  const fetchItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await itemsAPI.getPublicItems();

      // axios wraps the actual body in response.data
      // The backend /api/items/public returns a plain JSON array directly
      let data = response.data;

      // Safety: if for any reason data is wrapped in an object, unwrap it
      if (data && !Array.isArray(data)) {
        if (Array.isArray(data.items)) {
          data = data.items;
        } else if (Array.isArray(data.data)) {
          data = data.data;
        } else {
          console.error('Unexpected API response shape:', data);
          data = [];
        }
      }

      // Final safety net — never set a non-array into state
      const safeData = Array.isArray(data) ? data : [];
      setItems(safeData);
      setFilteredItems(safeData);
    } catch (err) {
      console.error('Failed to fetch items:', err);
      setError('Failed to load items. Please try again later.');
      // Always reset to arrays on error so .map() never crashes
      setItems([]);
      setFilteredItems([]);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Build the full image URL.
   * - If image_url is already absolute (starts with http/https), use as-is.
   * - If relative (e.g. /uploads/items/xxx.jpg), prepend BACKEND_URL.
   * - If null/undefined, return the fallback placeholder.
   */
  const getImageSrc = (image_url) => {
    const FALLBACK =
      'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=400';
    if (!image_url) return FALLBACK;
    if (image_url.startsWith('http://') || image_url.startsWith('https://')) {
      return image_url;
    }
    return `${BACKEND_URL}${image_url}`;
  };

  /**
   * Format the date for display.
   * Backend field is `created_date` (YYYY-MM-DD), NOT `date`.
   * Falls back to parsing `created_at` if `created_date` is missing.
   */
  const formatDate = (item) => {
    if (item.created_date) return item.created_date;
    if (item.created_at) {
      try {
        return new Date(item.created_at).toLocaleDateString('en-IN', {
          year: 'numeric',
          month: 'short',
          day: '2-digit',
        });
      } catch {
        return item.created_at;
      }
    }
    return '';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicHeader />

      {/* Hero Section */}
      <section className="relative bg-slate-900 text-white overflow-hidden">
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `url(${bgimg})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <div className="max-w-2xl">
            <h1 className="font-outfit text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 animate-fade-in">
              Campus Lost &amp; Found
            </h1>
            <p className="text-lg text-slate-300 mb-8 animate-fade-in">
              Browse recently lost and found items on campus. If you&apos;ve lost or found something,
              login to report it or claim an item.
            </p>

            {/* Search Bar */}
            <div className="relative animate-fade-in">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <Input
                type="text"
                placeholder="Search lost and found items by description or location..."
                className="pl-12 pr-4 py-6 text-base bg-white text-slate-900 border-0 rounded-lg shadow-lg"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                data-testid="public-search-input"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Items Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="font-outfit text-2xl font-bold text-slate-900">
              Recent Lost &amp; Found Items
            </h2>
            <p className="text-slate-500 mt-1">
              {Array.isArray(filteredItems) ? filteredItems.length : 0} items listed
            </p>
          </div>
          <Button
            onClick={() => navigate('/student/login')}
            className="bg-slate-900 hover:bg-slate-800"
            data-testid="login-to-claim-btn"
          >
            Login to Report / Claim
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="spinner" />
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <Package className="w-16 h-16 mx-auto text-red-300 mb-4" />
            <h3 className="text-lg font-medium text-slate-700 mb-2">Error loading items</h3>
            <p className="text-slate-500 mb-4">{error}</p>
            <Button onClick={fetchItems} variant="outline">
              Retry
            </Button>
          </div>
        ) : !Array.isArray(filteredItems) || filteredItems.length === 0 ? (
          <div className="text-center py-16">
            <Package className="w-16 h-16 mx-auto text-slate-300 mb-4" />
            <h3 className="text-lg font-medium text-slate-700 mb-2">No items found</h3>
            <p className="text-slate-500">
              {searchQuery ? 'Try a different search term' : 'Check back later for found items'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredItems.map((item, index) => (
              <div
                key={item.id}
                className="item-card animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`public-item-${item.id}`}
              >
                <div className="relative">
                  <img
                    src={getImageSrc(item.image_url)}
                    alt={item.description || 'Lost & Found item'}
                    className="item-card-image"
                    onError={(e) => {
                      e.target.onerror = null; // prevent infinite fallback loop
                      e.target.src =
                        'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=400';
                    }}
                  />
                  <Badge
                    className={`absolute top-3 left-3 ${
                      item.item_type === 'lost' ? 'status-lost' : 'status-found'
                    }`}
                  >
                    {item.item_type ? item.item_type.toUpperCase() : 'FOUND'}
                  </Badge>
                </div>
                <div className="p-4">
                  <p className="text-sm text-slate-800 font-medium line-clamp-2 mb-3">
                    {item.description}
                  </p>
                  <div className="space-y-1.5 text-xs text-slate-500">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{item.location}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 flex-shrink-0" />
                      {/* FIX: backend sends created_date, not item.date */}
                      <span>{formatDate(item)}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-8 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="font-outfit font-bold mb-1">
            ST. PETERS COLLEGE OF ENGINEERING AND TECHNOLOGY
          </p>
          <p className="text-sm text-slate-400">(AN AUTONOMOUS)</p>
          <p className="text-xs text-slate-500 mt-4">
            Lost &amp; Found Management System &copy; {new Date().getFullYear()}
          </p>
        </div>
      </footer>
    </div>
  );
};

export default PublicPage;
