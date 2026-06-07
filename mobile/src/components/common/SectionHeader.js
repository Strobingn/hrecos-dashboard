import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

export const SectionHeader = ({
  title,
  actionLabel,
  onAction,
  icon = null,
}) => {
  const { theme } = useTheme();

  return (
    <View style={styles.container}>
      <View style={styles.left}>
        {icon && (
          <MaterialCommunityIcons
            name={icon}
            size={18}
            color={theme.colors.primary}
            style={styles.icon}
          />
        )}
        <Text style={[styles.title, { color: theme.colors.text }]}>
          {title}
        </Text>
      </View>
      {actionLabel && onAction && (
        <TouchableOpacity onPress={onAction} style={styles.action} activeOpacity={0.7}>
          <Text style={[styles.actionText, { color: theme.colors.primary }]}>
            {actionLabel}
          </Text>
          <MaterialCommunityIcons
            name="chevron-right"
            size={16}
            color={theme.colors.primary}
          />
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    marginRight: 8,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
  },
  action: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionText: {
    fontSize: 13,
    fontWeight: '600',
  },
});
