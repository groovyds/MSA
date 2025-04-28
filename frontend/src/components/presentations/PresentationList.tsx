import React, { useEffect, useState } from 'react';
import { DocumentIcon, TrashIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

interface Presentation {
  id: string;
  filename: string;
  uploadDate: string;
}

interface PresentationListProps {
  onSelectPresentation: (id: string) => void;
  activePresentation: string | null;
}

export const PresentationList: React.FC<PresentationListProps> = ({
  onSelectPresentation,
  activePresentation,
}) => {
  const [presentations, setPresentations] = useState<Presentation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPresentations = async () => {
      try {
        const response = await fetch('/api/presentations');
        const data = await response.json();
        setPresentations(data);
      } catch (error) {
        console.error('Error fetching presentations:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPresentations();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/presentations/${id}`, {
        method: 'DELETE',
      });
      setPresentations((prev) => prev.filter((p) => p.id !== id));
    } catch (error) {
      console.error('Error deleting presentation:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 bg-gray-200 rounded-lg"
          />
        ))}
      </div>
    );
  }

  if (presentations.length === 0) {
    return (
      <div className="text-center py-8">
        <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          No presentations
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Upload a PowerPoint file to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {presentations.map((presentation) => (
        <div
          key={presentation.id}
          className={`flex items-center justify-between p-3 rounded-lg cursor-pointer ${
            activePresentation === presentation.id
              ? 'bg-primary-50 border border-primary-200'
              : 'hover:bg-gray-50'
          }`}
          onClick={() => onSelectPresentation(presentation.id)}
        >
          <div className="flex items-center space-x-3">
            <DocumentIcon className="h-5 w-5 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-900">
                {presentation.filename}
              </p>
              <p className="text-xs text-gray-500">
                {format(new Date(presentation.uploadDate), 'MMM d, yyyy')}
              </p>
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(presentation.id);
            }}
            className="p-1 text-gray-400 hover:text-red-500"
          >
            <TrashIcon className="h-5 w-5" />
          </button>
        </div>
      ))}
    </div>
  );
}; 