import { useParams } from "react-router-dom";

export default function EventDetail() {
  const { eventId } = useParams<{ eventId: string }>();
  return <div>Event {eventId}</div>;
}
