// 🐦 Flutter imports:
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// 📦 Package imports:
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

// 🌎 Project imports:
import 'package:comunityfitness/theme/app_theme.dart';
import 'package:comunityfitness/viewmodels/data_management_viewmodel.dart';
import 'package:comunityfitness/views/widgets/app_back_button.dart';

class DataManagementScreen extends ConsumerStatefulWidget {
  const DataManagementScreen({super.key});

  @override
  ConsumerState<DataManagementScreen> createState() => _DataManagementScreenState();
}

class _DataManagementScreenState extends ConsumerState<DataManagementScreen> {
  final _inputController = TextEditingController();

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(dataManagementViewModelProvider);
    final vm = ref.read(dataManagementViewModelProvider.notifier);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: AppBackButton.maybeLeading(context),
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: const Text(
          'Data & Migration',
          style: TextStyle(fontSize: AppDimensions.fontXL, fontWeight: FontWeight.w900, letterSpacing: 0.3, color: AppColors.textPrimary),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDimensions.paddingM),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status Cards
            Row(
              children: [
                Expanded(
                  child: _StatCard(title: 'Routines', value: '${state.totalRoutines}', icon: FontAwesomeIcons.clipboardList),
                ),
                const SizedBox(width: AppDimensions.paddingS),
                Expanded(
                  child: _StatCard(title: 'Workouts', value: '${state.totalSessions}', icon: FontAwesomeIcons.dumbbell),
                ),
                const SizedBox(width: AppDimensions.paddingS),
                Expanded(
                  child: _StatCard(title: 'Exercises', value: '${state.totalExercises}', icon: FontAwesomeIcons.bookBookmark),
                ),
              ],
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Backup & Export Section
            const Text(
              'BACKUP & EXPORT',
              style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            _ActionCard(
              title: 'Export Full JSON Backup',
              description: 'Export all routines, workouts, and custom exercises to JSON.',
              icon: FontAwesomeIcons.fileArrowDown,
              iconColor: AppColors.primary,
              onTap: () {
                final json = vm.exportFullBackupJson();
                Clipboard.setData(ClipboardData(text: json));
                ScaffoldMessenger.of(context)
                    .showSnackBar(const SnackBar(content: Text('Backup copied to clipboard!'), backgroundColor: AppColors.surfaceElevated));
              },
            ),
            const SizedBox(height: AppDimensions.paddingL),

            // Import Section
            const Text(
              'IMPORT & MIGRATE HISTORY',
              style: TextStyle(fontSize: AppDimensions.fontXS, fontWeight: FontWeight.w900, letterSpacing: 1.2, color: AppColors.textMuted),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            _ActionCard(
              title: 'Import JSON Backup',
              description: 'Restore routines and sessions from CommunityFitness or OpenGym backup.',
              icon: FontAwesomeIcons.fileCode,
              iconColor: AppColors.secondary,
              onTap: () =>
                  _showImportDialog(title: 'Import JSON Backup', hint: 'Paste JSON content here...', onConfirm: (text) => vm.importBackupJson(text)),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            _ActionCard(
              title: 'Import from Hevy (CSV)',
              description: 'Migrate your historical workout logs from Hevy CSV export.',
              icon: FontAwesomeIcons.fileCsv,
              iconColor: AppColors.primary,
              onTap: () =>
                  _showImportDialog(title: 'Import Hevy CSV', hint: 'Paste Hevy CSV content here...', onConfirm: (text) => vm.importHevyCsv(text)),
            ),
            const SizedBox(height: AppDimensions.paddingS),

            _ActionCard(
              title: 'Import from Strong (CSV)',
              description: 'Migrate your historical workout logs from Strong CSV export.',
              icon: FontAwesomeIcons.fileCsv,
              iconColor: AppColors.warning,
              onTap: () => _showImportDialog(
                title: 'Import Strong CSV',
                hint: 'Paste Strong CSV content here...',
                onConfirm: (text) => vm.importStrongCsv(text),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showImportDialog({required String title, required String hint, required Future<void> Function(String) onConfirm}) {
    _inputController.clear();
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surfaceElevated,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          side: const BorderSide(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        title: Text(
          title,
          style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
        ),
        content: SizedBox(
          width: double.maxFinite,
          child: TextField(
            controller: _inputController,
            maxLines: 8,
            style: const TextStyle(color: AppColors.textPrimary, fontSize: AppDimensions.fontS),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(color: AppColors.textMuted),
            ),
          ),
        ),
        actions: [
          TextButton(
            child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary)),
            onPressed: () => Navigator.pop(context),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: AppColors.background,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppDimensions.radiusCard)),
            ),
            child: const Text('Import', style: TextStyle(fontWeight: FontWeight.bold)),
            onPressed: () async {
              final text = _inputController.text.trim();
              if (text.isNotEmpty) {
                final messenger = ScaffoldMessenger.of(context);
                Navigator.pop(context);
                try {
                  await onConfirm(text);
                  if (mounted) {
                    messenger.showSnackBar(
                      const SnackBar(content: Text('Import completed successfully!'), backgroundColor: AppColors.surfaceElevated),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    messenger.showSnackBar(SnackBar(content: Text('Error: $e'), backgroundColor: AppColors.error));
                  }
                }
              }
            },
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final FaIconData icon;

  const _StatCard({required this.title, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppDimensions.paddingM),
      decoration: BoxDecoration(
        color: AppColors.surfaceElevated,
        borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
        border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
      ),
      child: Column(
        children: [
          FaIcon(icon, size: AppDimensions.iconM, color: AppColors.primary),
          const SizedBox(height: AppDimensions.paddingXS),
          Text(
            value,
            style: const TextStyle(fontSize: AppDimensions.fontL, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
          ),
          Text(
            title,
            style: const TextStyle(fontSize: AppDimensions.fontXXS, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final String title;
  final String description;
  final FaIconData icon;
  final Color iconColor;
  final VoidCallback onTap;

  const _ActionCard({required this.title, required this.description, required this.icon, required this.iconColor, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
      child: Container(
        padding: const EdgeInsets.all(AppDimensions.paddingM),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(AppDimensions.radiusCard),
          border: Border.all(color: AppColors.border, width: AppDimensions.borderDefault),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(AppDimensions.paddingM),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppDimensions.radiusS),
                border: Border.all(color: AppColors.borderSubtle, width: AppDimensions.borderThin),
              ),
              child: FaIcon(icon, size: AppDimensions.iconM, color: iconColor),
            ),
            const SizedBox(width: AppDimensions.paddingM),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: AppDimensions.fontM, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: AppDimensions.paddingXXS),
                  Text(
                    description,
                    style: const TextStyle(fontSize: AppDimensions.fontXS, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
            const FaIcon(FontAwesomeIcons.chevronRight, size: AppDimensions.iconXS, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}
