import { useState, useEffect } from 'react';
import { itemsAPI, getErrorMessage } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { Search, Eye, MapPin, Calendar, Trash2 } from 'lucide-react';
import { NO_IMAGE_PLACEHOLDER } from '../lib/utils';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://lostnfound-clg-main.onrender.com';

const AdminLostItems = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [itemToDelete, setItemToDelete] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchItems();
  }, []);

  const handleDelete = async () => {
    if (!deleteReason.trim() || !itemToDelete) return;
    setDeleting(true);
    try {
      await itemsAPI.deleteItem(itemToDelete.id, deleteReason);
      toast.success('Item deleted successfully');
      setShowDeleteDialog(false);
      setItemToDelete(null);
      setDeleteReason('');
      fetchItems();
    } catch (error) {
      console.error('Failed to delete item:', error);
      toast.error(getErrorMessage(error, 'Failed to delete item'));
    } finally {
      setDeleting(false);
    }
  };

  const fetchItems = async () => {
    try {
      const response = await itemsAPI.getItems({ item_type: 'lost' });
      setItems(response.data);
    } catch (error) {
      console.error('Failed to fetch items:', error);
      toast.error('Failed to load items');
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = items.filter(item =>
    item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.student?.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.student?.roll_number?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active': return <Badge className="status-lost">Active</Badge>;
      case 'claimed': return <Badge className="status-claimed">Claimed</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="admin-lost-items">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-900">Lost Items</h1>
          <p className="text-slate-500">{items.length} items reported</p>
        </div>
        <div className="relative max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
            data-testid="search-input"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="spinner" />
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center py-12">
              <Search className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">No lost items found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table className="min-w-[700px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Image</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Student</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredItems.map((item) => (
                    <TableRow key={item.id} className="table-row-hover" data-testid={`item-row-${item.id}`}>
                      <TableCell>
                        <img
                          src={item.image_url ? `${BACKEND_URL}${item.image_url}` : NO_IMAGE_PLACEHOLDER}
                          alt=""
                          className="w-12 h-12 rounded-lg object-cover"
                          onError={(e) => {
                            e.target.src = NO_IMAGE_PLACEHOLDER;
                          }}
                        />
                      </TableCell>
                      <TableCell className="max-w-xs">
                        <p className="truncate">{item.description}</p>
                      </TableCell>
                      <TableCell>
                        <span className="flex items-center gap-1 text-sm">
                          <MapPin className="w-3 h-3" />
                          {item.location}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="flex items-center gap-1 text-sm mono">
                          <Calendar className="w-3 h-3" />
                          {item.date}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.student && (
                          <div>
                            <p className="text-sm font-medium">{item.student.full_name}</p>
                            <p className="text-xs text-slate-500 mono">{item.student.roll_number}</p>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{getStatusBadge(item.status)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedItem(item)}
                            data-testid={`view-item-${item.id}`}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          {item.status === 'active' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setItemToDelete(item);
                                setShowDeleteDialog(true);
                              }}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              data-testid={`delete-item-${item.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Item Detail Dialog */}
      <Dialog open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Lost Item Details</DialogTitle>
          </DialogHeader>
          {selectedItem && (
            <div className="space-y-4">
              <img
                src={selectedItem.image_url ? `${BACKEND_URL}${selectedItem.image_url}` : NO_IMAGE_PLACEHOLDER}
                alt=""
                className="w-full max-h-64 object-cover rounded-lg"
                onError={(e) => {
                  e.target.src = NO_IMAGE_PLACEHOLDER;
                }}
              />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500">Description</p>
                  <p className="text-sm">{selectedItem.description}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Location</p>
                  <p className="text-sm">{selectedItem.location}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Date</p>
                  <p className="text-sm mono">{selectedItem.date}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Time</p>
                  <p className="text-sm mono">{selectedItem.time}</p>
                </div>
                {selectedItem.student && (
                  <>
                    <div>
                      <p className="text-xs text-slate-500">Reported By</p>
                      <p className="text-sm">{selectedItem.student.full_name}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Roll Number</p>
                      <p className="text-sm mono">{selectedItem.student.roll_number}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Lost Item</DialogTitle>
            <DialogDescription>
              Please provide a reason for deleting this item. This action will be logged in the audit trail.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="deleteReason">Reason for deletion *</Label>
              <Textarea
                id="deleteReason"
                placeholder="e.g., Reported in error, duplicate posting, resolved by hand, etc."
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                data-testid="delete-reason-input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => {
              setShowDeleteDialog(false);
              setItemToDelete(null);
              setDeleteReason('');
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleDelete} 
              disabled={!deleteReason.trim() || deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
              data-testid="confirm-delete-btn"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminLostItems;
