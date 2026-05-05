import { useParams } from "react-router-dom";

export default function AccountDetail() {
  const { eventId, accountId } = useParams<{
    eventId: string;
    accountId: string;
  }>();
  return (
    <div>
      Event {eventId} / Account {accountId}
    </div>
  );
}
