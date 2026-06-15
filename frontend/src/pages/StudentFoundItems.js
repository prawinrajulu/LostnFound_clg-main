import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { itemsAPI, claimsAPI } from '../services/api';
import { ItemGrid } from '../components/ItemCard';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Search, Package, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const StudentFoundItems = () => {
  const { user, token } = useAuth();
  const [items, setItems] = useState([]);
  const [filteredItems, setFilteredItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchFoundItems();
  }, []);

  useEffect(() => {
    filterItems();
  }, [searchQuery, items]);

  const fetchFoundItems = async () => {
    try {
      const response = await itemsAPI.getPublicItems();
      // Filter only found items
      const foundItems = response.data.filter(item => item.item_type === 'found');
      setItems(foundItems);
      setFilteredItems(foundItems);
    } catch (error) {
      console.error('Failed to fetch found items:', error);
      toast.error('Failed to load found items');
    } finally {
      setLoading(false);
    }
  };

  const filterItems = () => {
    if (!searchQuery.trim()) {
      setFilteredItems(items);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = items.filter(item =>
      item.description?.toLowerCase().includes(query) ||
      item.location?.toLowerCase().includes(query) ||
      item.created_date?.includes(query)
    );
    setFilteredItems(filtered);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Package className="w-7 h-7 text-emerald-600" />
            Found Items
          </h1>
          <p className="text-slate-500 mt-1">
            Browse items found on campus - claim if it's yours!
          </p>
        </div>
        <Badge variant="outline" className="w-fit">
          {filteredItems.length} {filteredItems.length === 1 ? 'Item' : 'Items'}
        </Badge>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <Input
          type="text"
          placeholder="Search by description, location, or date..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Items Grid */}
      {filteredItems.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg border border-slate-200">
          <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="font-semibold text-slate-900 mb-2">No Found Items</h3>
          <p className="text-slate-500">
            {searchQuery ? 'Try adjusting your search' : 'No found items have been reported yet'}
          </p>
        </div>
      ) : (
        <ItemGrid items={filteredItems} onUpdate={fetchFoundItems} showClaimButton={true} />
      )}
    </div>
  );
};

export default StudentFoundItems;
