from django.db import models
from django.contrib.auth.models import User


class FifaVersion(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Ex: "FIFA 14", "FC 24"

    def __str__(self): return self.name


class Player(models.Model):
    version = models.ForeignKey(FifaVersion, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    position = models.CharField(max_length=10)
    overall = models.IntegerField()
    pace = models.IntegerField(default=0)
    shooting = models.IntegerField(default=0)
    passing = models.IntegerField(default=0)
    dribbling = models.IntegerField(default=0)
    defending = models.IntegerField(default=0)
    physical = models.IntegerField(default=0)

    class Meta:
        ordering = ['-overall']


class Draft(models.Model):
    name = models.CharField(max_length=100)  # Ex: "Draft Copa Farid - 1ª Edição"
    version = models.ForeignKey(FifaVersion, on_delete=models.CASCADE)
    current_pick_number = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)


class DraftOrder(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    president = models.ForeignKey(User, on_delete=models.CASCADE)
    pick_order = models.IntegerField()  # 1 a 13
    formation = models.CharField(max_length=15, default='4-3-3')
    class Meta:
        ordering = ['pick_order']


class Pick(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    president = models.ForeignKey(User, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    pick_number = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    lineup_slot = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.pick_number} - {self.player.name}"


class TradeOffer(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE)
    proposer = models.ForeignKey(User, related_name='proposed_trades', on_delete=models.CASCADE)
    target = models.ForeignKey(User, related_name='received_trades', on_delete=models.CASCADE)

    offered_picks = models.ManyToManyField(Pick, related_name='offered_in_trades')
    requested_picks = models.ManyToManyField(Pick, related_name='requested_in_trades')

    status = models.CharField(max_length=20, default='PENDING')  # PENDING, ACCEPTED, REJECTED, CANCELED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Troca: {self.proposer.username} -> {self.target.username} ({self.status})"